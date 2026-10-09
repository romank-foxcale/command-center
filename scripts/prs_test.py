#!/usr/bin/env python3
"""Test ./cc prs with a fake gh: only catalog repos are queried, newest first, new and updated PRs are marked."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "prs.py"

# The fake gh logs which repo it was asked about and answers from PULLS (a JSON file the test rewrites).
FAKE_GH = f"""#!{sys.executable}
import json, os, sys
if sys.argv[1:3] == ["api", "user"]:
    print("me")
    sys.exit(0)
if sys.argv[1:3] == ["api", "graphql"]:  # review threads: none here; threads_test.py covers them
    print(json.dumps({{"data": {{"repository": {{"pullRequest": {{"number": 1, "title": "t", "author": {{"login": "dev"}}}}}}}}}}))
    sys.exit(0)
repo = sys.argv[sys.argv.index("--repo") + 1]
if sys.argv[1:3] == ["pr", "view"]:
    print(json.dumps(json.load(open(os.environ["FAKE_GH_PULLS"]))["view"]))
    sys.exit(0)
if sys.argv[1:3] == ["pr", "diff"]:
    print("diff --git a/api.py b/api.py")
    sys.exit(0)
with open(os.environ["FAKE_GH_LOG"], "a") as log:
    log.write(repo + "\\n")
pulls = json.load(open(os.environ["FAKE_GH_PULLS"]))
if repo not in pulls:
    sys.exit("could not resolve to a Repository")
print(json.dumps(pulls[repo]))
"""


def pr(number: int, created: str, updated: str | None = None, **extra: object) -> dict:
    return {"number": number, "title": f"PR {number}", "author": {"login": "dev"}, "createdAt": created,
            "updatedAt": updated or created, "isDraft": False, "reviewDecision": "REVIEW_REQUIRED",
            "url": f"https://github.com/foxcale/x/pull/{number}", "baseRefName": "develop", "headRefName": f"f{number}", **extra}


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        root = base / "pv_CC"
        for identifier, remote in (("pv-frontend", "https://github.com/foxcale/foxcope-PV-frontend.git"),
                                   ("pv-backend", "git@github.com:foxcale/foxcope-PV-backend.git"),
                                   ("pv-internal", "https://gitlab.example.com/pv/internal.git")):
            path = root / "catalog" / "repositories" / f"{identifier}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"id": identifier, "remote": remote}))
        # A sibling CC's clone in the shared ../repos/ folder: it must never be queried.
        (base / "repos" / "di-backend" / ".git").mkdir(parents=True)

        bin_dir = base / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text(FAKE_GH)
        (bin_dir / "gh").chmod(0o755)
        log, pulls = base / "gh.log", base / "pulls.json"
        pulls.write_text(json.dumps({
            "foxcale/foxcope-PV-frontend": [pr(7, "2026-10-01T10:00:00Z", isDraft=True)],
            "foxcale/foxcope-PV-backend": [pr(3, "2026-10-02T10:00:00Z"), pr(4, "2026-10-07T09:00:00Z")],
        }))
        env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "FAKE_GH_LOG": str(log), "FAKE_GH_PULLS": str(pulls)}

        def listing() -> tuple[list[dict], str]:
            result = subprocess.run([sys.executable, str(SCRIPT), str(root), "--json"], capture_output=True, text=True, env=env)
            assert result.returncode == 0, result.stderr
            return json.loads(result.stdout), result.stderr

        rows, warnings = listing()
        assert sorted(set(log.read_text().split())) == ["foxcale/foxcope-PV-backend", "foxcale/foxcope-PV-frontend"], \
            f"only the catalog's GitHub repos are queried: {log.read_text()}"
        assert "pv-internal: not a GitHub remote" in warnings, warnings
        assert "review threads not checked" not in warnings, warnings
        assert all(row["threads"] == "" for row in rows), "no review threads, nothing waits"
        assert [(row["repo"], row["number"]) for row in rows] == [("pv-backend", 4), ("pv-backend", 3), ("pv-frontend", 7)], \
            "newest first across repos"
        assert all(row["seen"] == "new" for row in rows), "everything is new on the first listing"
        assert rows[2]["review"] == "draft" and rows[0]["review"] == "review required"

        # Second listing: nothing new; a PR that changed since is marked updated; a brand-new one is new.
        current = json.loads(pulls.read_text())
        current["foxcale/foxcope-PV-backend"][1]["updatedAt"] = "2026-10-07T12:00:00Z"
        current["foxcale/foxcope-PV-frontend"].append(pr(8, "2026-10-07T11:00:00Z"))
        pulls.write_text(json.dumps(current))
        rows, _ = listing()
        marks = {(row["repo"], row["number"]): row["seen"] for row in rows}
        assert marks == {("pv-frontend", 8): "new", ("pv-backend", 4): "updated", ("pv-backend", 3): "", ("pv-frontend", 7): ""}, marks

        # show: what a review needs, with Trello cards linked from the description or comments.
        current["view"] = {**pr(4, "2026-10-07T09:00:00Z"), "body": "Implements https://trello.com/c/Cd1/7-health.",
                           "comments": [{"body": "see also https://trello.com/c/Xy9"}], "additions": 5, "deletions": 1,
                           "files": [{"path": "api.py", "additions": 5, "deletions": 1}]}
        pulls.write_text(json.dumps(current))
        detail = subprocess.run([sys.executable, str(SCRIPT), str(root), "show", "pv-backend", "4", "--diff"],
                                capture_output=True, text=True, env=env)
        assert detail.returncode == 0, detail.stderr
        assert "trello: https://trello.com/c/Cd1/7-health, https://trello.com/c/Xy9" in detail.stdout, detail.stdout
        assert "+5 -1  api.py" in detail.stdout and "diff --git a/api.py" in detail.stdout, detail.stdout
        outside = subprocess.run([sys.executable, str(SCRIPT), str(root), "show", "di-backend", "1"], capture_output=True, text=True, env=env)
        assert outside.returncode != 0 and "not in the catalog" in outside.stderr, "show is limited to the catalog too"

        unknown = subprocess.run([sys.executable, str(SCRIPT), str(root), "di-backend"], capture_output=True, text=True, env=env)
        assert unknown.returncode != 0 and "not in the catalog" in unknown.stderr, "a repo outside the catalog is refused"

        check_checkout(base, root, env)
    print("prs test passed")


def git(path: Path, *arguments: str) -> str:
    result = subprocess.run(["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@t", *arguments],
                            capture_output=True, text=True)
    assert result.returncode == 0, f"git {arguments}: {result.stderr}"
    return result.stdout.strip()


def check_checkout(base: Path, root: Path, env: dict[str, str]) -> None:
    """checkout puts the PR head into a feature worktree, follows later pushes, and cleans up without complaint."""
    (root / "control-center.json").write_text(json.dumps(
        {"name": "pv_CC", "layout": {"projectsRoot": "..", "repositories": "../repos", "worktrees": "../worktrees"}}))
    descriptor = root / "catalog/repositories/pv-backend.json"
    descriptor.write_text(json.dumps({**json.loads(descriptor.read_text()), "checkout": "pv-backend", "defaultBranch": "develop",
                                      "sourceInput": "pv-backend"}))
    # GitHub keeps each PR's head at refs/pull/<n>/head; a bare repo plays GitHub.
    author = base / "author"
    git(base, "init", "-q", "-b", "develop", str(author))
    git(author, "commit", "-q", "--allow-empty", "-m", "base")
    origin = base / "origin.git"
    git(base, "clone", "-q", "--bare", str(author), str(origin))
    git(author, "commit", "-q", "--allow-empty", "-m", "pr 4, first push")
    git(author, "push", "-q", str(origin), "HEAD:refs/pull/4/head")
    git(base, "clone", "-q", str(origin), str(base / "repos" / "pv-backend"))

    def checkout() -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), str(root), "checkout", "pv-backend", "4"], capture_output=True, text=True, env=env)

    first = checkout()
    assert first.returncode == 0, first.stderr
    worktree = base / "worktrees" / "pr-pv-backend-4" / "pv-backend_wt"
    assert git(worktree, "log", "-1", "--format=%s") == "pr 4, first push", "the worktree is at the PR head"
    manifest = json.loads((base / "worktrees/pr-pv-backend-4/.cc-worktree.json").read_text())
    assert manifest["trelloCard"] == "https://trello.com/c/Cd1/7-health", "the PR's card is linked for cc-trello"
    assert manifest["review"] is True, "a PR checkout is marked as a review checkout"
    guard = (base / "worktrees/pr-pv-backend-4/CLAUDE.md").read_text()
    assert "review checkout" in guard and "Never edit, commit or push" in guard, guard

    git(author, "commit", "-q", "--allow-empty", "-m", "pr 4, second push")
    git(author, "push", "-q", str(origin), "HEAD:refs/pull/4/head")
    second = checkout()
    assert second.returncode == 0 and "updated" in second.stdout, second.stderr
    assert git(worktree, "log", "-1", "--format=%s") == "pr 4, second push", "re-running follows the PR's latest push"

    removed = subprocess.run([sys.executable, str(SCRIPT.parent / "worktrees.py"), str(root), "remove", "pr-pv-backend-4"],
                             capture_output=True, text=True)
    assert removed.returncode == 0, f"the PR's commits are published, so cleanup must not refuse: {removed.stderr}"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

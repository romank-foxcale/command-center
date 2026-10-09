#!/usr/bin/env python3
"""Test ./cc migrate-layout on real git clones and worktrees: this CC's clones and features move into its
folder and keep working, another CC's stay where they are, a clone two catalogs share is refused before
anything moves, and a second run changes nothing."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
OLD = {"projectsRoot": "..", "repositories": "../repos", "worktrees": "../worktrees", "worktreePattern": "{feature}/{repository}_wt"}


def run(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(arguments, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise AssertionError(f"{arguments}: {result.stdout}{result.stderr}")
    return result


def git(directory: Path, *arguments: str) -> str:
    return run("git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(directory), *arguments).stdout.strip()


def make_cc(projects: Path, name: str, identifiers: list[str]) -> Path:
    root = projects / name
    (root / "catalog" / "repositories").mkdir(parents=True)
    (root / "control-center.json").write_text(json.dumps({"schemaVersion": 1, "name": name, "status": "ready", "layout": OLD}))
    for identifier in identifiers:
        (root / "catalog" / "repositories" / f"{identifier}.json").write_text(json.dumps({
            "id": identifier, "checkout": identifier, "kind": "project", "defaultBranch": "main", "sourceInput": identifier}))
    return root


def clone(projects: Path, identifier: str) -> None:
    origin = projects.parent / f"{identifier}.git"
    seed = projects.parent / f"{identifier}-seed"
    run("git", "init", "-q", "-b", "main", str(seed))
    git(seed, "commit", "-q", "--allow-empty", "-m", "base")
    run("git", "clone", "-q", "--bare", str(seed), str(origin))
    run("git", "clone", "-q", str(origin), str(projects / "repos" / identifier))


def migrate(root: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    return run(sys.executable, str(SCRIPTS / "migrate_layout.py"), str(root), *flags, check=False)


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        projects = Path(directory) / "Projects"
        (projects / "repos").mkdir(parents=True)
        pv = make_cc(projects, "pv_CC", ["pv-backend"])
        di = make_cc(projects, "di_CC", ["ai"])
        clone(projects, "pv-backend")
        clone(projects, "ai")
        worktrees = lambda root, *arguments: run(sys.executable, str(SCRIPTS / "worktrees.py"), str(root), *arguments)
        worktrees(pv, "create", "beta-db", "pv-backend")
        worktrees(di, "create", "flar", "ai")
        old_feature = projects / "worktrees" / "beta-db"
        git(old_feature / "pv-backend_wt", "commit", "-q", "--allow-empty", "-m", "work in progress")
        head = git(old_feature / "pv-backend_wt", "rev-parse", "HEAD")
        run_dir = old_feature / ".cc-runs" / "r1"
        run_dir.mkdir(parents=True)
        (run_dir / "state.json").write_text(json.dumps({"worktree": str(old_feature / "pv-backend_wt"), "stage": "done"}))

        dry = migrate(pv, "--dry-run")
        assert dry.returncode == 0 and "pv-backend" in dry.stdout and (projects / "repos" / "pv-backend").exists(), dry.stdout

        moved = migrate(pv)
        assert moved.returncode == 0, moved.stderr
        feature = pv / "worktrees" / "beta-db"
        assert (pv / "repos" / "pv-backend" / ".git").is_dir() and not (projects / "repos" / "pv-backend").exists()
        assert git(feature / "pv-backend_wt", "rev-parse", "HEAD") == head, "the worktree keeps its commits"
        assert git(feature / "pv-backend_wt", "branch", "--show-current") == "beta-db"
        listed = git(pv / "repos" / "pv-backend", "worktree", "list", "--porcelain")
        assert f"worktree {feature / 'pv-backend_wt'}" in listed and "prunable" not in listed, listed
        manifest = json.loads((feature / ".cc-worktree.json").read_text())
        assert manifest["repositories"]["pv-backend"]["base"] == "repos/pv-backend"
        assert manifest["repositories"]["pv-backend"]["worktree"] == "worktrees/beta-db/pv-backend_wt"
        assert json.loads((feature / ".cc-runs/r1/state.json").read_text())["worktree"] == str(feature / "pv-backend_wt")
        assert str(old_feature) not in (feature / "CLAUDE.md").read_text(), "the session guard names the new place"
        assert json.loads((pv / "control-center.json").read_text())["layout"]["repositories"] == "repos"
        assert "/repos/" in (pv / ".gitignore").read_text() and "/worktrees/" in (pv / ".gitignore").read_text()
        status = worktrees(pv, "status", "beta-db")
        assert "beta-db" in status.stdout and "pv-backend" in status.stdout, status.stdout

        # The other CC is untouched until it migrates itself.
        assert (projects / "repos" / "ai").is_dir() and (projects / "worktrees" / "flar" / "ai_wt").is_dir()
        assert migrate(pv).stdout.startswith("already on the per-CC layout"), "a second run changes nothing"

        # A clone listed by two catalogs is refused before anything moves.
        (pv / "catalog" / "repositories" / "ai.json").write_text((di / "catalog" / "repositories" / "ai.json").read_text())
        shared = make_cc(projects, "x_CC", ["ai"])
        refused = migrate(shared)
        assert refused.returncode != 0 and "di_CC" in refused.stderr and (projects / "repos" / "ai").is_dir(), refused.stderr

        moved = migrate(di)
        assert moved.returncode != 0 and "x_CC" in moved.stderr, "di shares ai with x_CC now"
        (shared / "catalog" / "repositories" / "ai.json").unlink()
        moved = migrate(di)
        assert moved.returncode == 0, moved.stderr
        assert git(di / "worktrees" / "flar" / "ai_wt", "branch", "--show-current") == "flar"
        assert not (projects / "repos").exists() and not (projects / "worktrees").exists(), "empty shared folders are removed"
    print("migrate layout test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

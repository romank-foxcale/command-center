#!/usr/bin/env python3
"""Test ./cc repo add by URL, set-branch, remove and the reference kind against local bare Git remotes."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def run(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(arguments, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise AssertionError(f"{arguments} failed:\n{result.stdout}{result.stderr}")
    return result


def bare_remote(base: Path, name: str, branch: str) -> str:
    """A remote whose HEAD is `branch`, like a GitHub repo whose main branch is develop."""
    source = base / f"{name}-src"
    run("git", "init", "-q", "-b", branch, str(source))
    (source / "README.md").write_text(f"# {name}\n")
    (source / "docs").mkdir()
    (source / "docs" / "notes.md").write_text("notes\n")
    run("git", "-C", str(source), "add", "-A")
    run("git", "-C", str(source), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    remote = base / f"{name}.git"
    run("git", "clone", "-q", "--bare", str(source), str(remote))
    return remote.as_uri()


def writable(path: Path) -> bool:
    try:
        path.write_text(path.read_text() + "x") if path.is_file() else (path / "new.txt").write_text("x")
        return True
    except PermissionError:
        return False


def check_reference_clone(base: Path, root: Path, repo) -> None:
    """A reference clone sits in repos/reference/, nobody can write its files, and update and set-kind
    still work: the protection is lifted only for the moment they need it."""
    clone = root / "repos" / "reference" / "foxcope-pv-poc"
    readme = clone / "README.md"
    assert readme.is_file(), "cloned with its files"
    assert not writable(readme) and not writable(clone) and not writable(clone / "docs"), "files and folders are read-only"
    assert os.access(clone / ".git", os.W_OK), ".git stays writable so fetching works"

    source = base / "foxcope-PV-PoC-src"
    (source / "README.md").write_text("# PoC\n\nversion 2\n")
    run("git", "-C", str(source), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "v2")
    run("git", "-C", str(source), "push", "-q", str(base / "foxcope-PV-PoC.git"), "main")
    repo("update", "foxcope-pv-poc")
    assert "version 2" in readme.read_text() and not writable(readme), "update fast-forwards and protects again"

    repo("set-kind", "foxcope-pv-poc", "project", check=False)  # refused: a project needs targets and a stack
    repo("set-targets", "foxcope-pv-poc", "linux")
    repo("set-stack", "foxcope-pv-poc", "csharp")
    repo("set-kind", "foxcope-pv-poc", "project")
    moved = root / "repos" / "project" / "foxcope-pv-poc"
    assert not clone.exists() and writable(moved / "README.md"), "a project clone is writable again"
    run("git", "-C", str(moved), "checkout", "-q", "--", ".")
    repo("set-kind", "foxcope-pv-poc", "reference")
    assert clone.is_dir() and not writable(readme), "back to reference: moved and protected"


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        root = base / "x_CC"
        (root / "catalog" / "repositories").mkdir(parents=True)
        (root / "control-center.json").write_text(json.dumps(
            {"name": "x_CC", "layout": {"projectsRoot": ".", "repositories": "repos", "worktrees": "worktrees"}}))
        repo = lambda *arguments, check=True: run(sys.executable, str(SCRIPTS / "repositories.py"), str(root), *arguments, check=check)
        backend = bare_remote(base, "Foxcope-PV-Backend", "develop")
        poc = bare_remote(base, "foxcope-PV-PoC", "main")

        # Pasting the link is enough: the id comes from the URL, the main branch from the remote's HEAD.
        repo("add", backend, "--targets", "linux", "--stack", "java")
        descriptor = json.loads((root / "catalog/repositories/foxcope-pv-backend.json").read_text())
        assert descriptor["id"] == "foxcope-pv-backend", descriptor
        assert descriptor["defaultBranch"] == "develop", "the main branch is read from the remote, not assumed to be main"
        assert descriptor["kind"] == "project" and descriptor["remote"] == backend

        assert repo("add", poc, check=False).returncode != 0, "a project repo still needs targets and a stack"
        repo("add", poc, "--kind", "reference", "--clone")
        assert json.loads((root / "catalog/repositories/foxcope-pv-poc.json").read_text())["targets"] == []
        check_reference_clone(base, root, repo)

        listing = repo("list").stdout
        assert "foxcope-pv-backend\tproject\tdevelop" in listing and "foxcope-pv-poc\treference\tmain" in listing, listing

        # set-branch refuses a branch the remote does not have, so a typo cannot break ./cc worktree.
        assert repo("set-branch", "foxcope-pv-backend", "mian", check=False).returncode != 0
        repo("set-branch", "foxcope-pv-backend", "develop")

        # Reference repos are never checked out as feature worktrees.
        refused = run(sys.executable, str(SCRIPTS / "worktrees.py"), str(root), "create", "demo", "foxcope-pv-poc", check=False)
        assert refused.returncode != 0 and "reference repo" in refused.stderr, refused.stderr

        # remove keeps the clone and refuses while a feature still uses the repo.
        feature = root / "worktrees" / "demo"
        feature.mkdir(parents=True)
        (feature / ".cc-worktree.json").write_text(json.dumps({"repositories": {"foxcope-pv-backend": {}}}))
        blocked = repo("remove", "foxcope-pv-backend", check=False)
        assert blocked.returncode != 0 and "demo" in blocked.stderr, blocked.stderr
        repo("remove", "foxcope-pv-poc")
        assert not (root / "catalog/repositories/foxcope-pv-poc.json").exists()
        assert (root / "repos" / "reference" / "foxcope-pv-poc" / ".git").exists(), "remove never deletes the base clone"

        # The kept clone is now outside the catalog: verify and doctor must say so.
        strays = repo("strays", check=False)
        assert strays.returncode != 0 and "foxcope-pv-poc" in strays.stderr, strays.stderr
        run("chmod", "-R", "u+w", str(root / "repos" / "reference" / "foxcope-pv-poc"))
        shutil.rmtree(root / "repos" / "reference" / "foxcope-pv-poc")
        assert repo("strays").returncode == 0, "repos/ matches the catalog again"
        (root / "repos" / "scratch").mkdir()
        assert "scratch" in repo("strays", check=False).stderr, "only project/ and reference/ belong in repos/"
    print("repositories test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

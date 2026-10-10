#!/usr/bin/env python3
"""Test ./cc migrate-layout on real git clones and worktrees. From the shared ../repos and ../worktrees, this
CC's clones land in repos/<kind>/<id> and its features in worktrees/ and keep working, a reference clone
becomes read-only, another CC's stay where they are, a clone two catalogs share is refused before anything
moves, and a second run changes nothing. From the flat repos/<id> of the first per-CC layout, clones are
nested under their kind and worktrees follow."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
OLD = {"projectsRoot": "..", "repositories": "../repos", "worktrees": "../worktrees", "worktreePattern": "{feature}/{repository}_wt"}
FLAT = {"projectsRoot": ".", "repositories": "repos", "worktrees": "worktrees", "worktreePattern": "{feature}/{repository}_wt"}


def run(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(arguments, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise AssertionError(f"{arguments}: {result.stdout}{result.stderr}")
    return result


def git(directory: Path, *arguments: str) -> str:
    return run("git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(directory), *arguments).stdout.strip()


def make_cc(projects: Path, name: str, repos: dict[str, str], layout: dict[str, str] = OLD) -> Path:
    root = projects / name
    (root / "catalog" / "repositories").mkdir(parents=True)
    (root / "control-center.json").write_text(json.dumps({"schemaVersion": 1, "name": name, "status": "ready", "layout": layout}))
    for identifier, kind in repos.items():
        (root / "catalog" / "repositories" / f"{identifier}.json").write_text(json.dumps({
            "id": identifier, "checkout": identifier, "kind": kind, "defaultBranch": "main", "sourceInput": identifier}))
    return root


def clone(into: Path, identifier: str) -> Path:
    origin = into.parent.parent / f"{identifier}.git"
    seed = into.parent.parent / f"{identifier}-seed"
    if not origin.exists():
        run("git", "init", "-q", "-b", "main", str(seed))
        (seed / "README.md").write_text(f"# {identifier}\n")
        git(seed, "add", "-A")
        git(seed, "commit", "-q", "-m", "base")
        run("git", "clone", "-q", "--bare", str(seed), str(origin))
    run("git", "clone", "-q", str(origin), str(into / identifier))
    return into / identifier


def feature(cc: Path, base: Path, feature_root: Path, name: str, identifier: str, relative_to: Path) -> Path:
    """A feature as the old ./cc worktree made it: a worktree, its manifest, a session guard and a council run."""
    worktree = feature_root / name / f"{identifier}_wt"
    git(base, "worktree", "add", "-q", "-b", name, str(worktree), "origin/main")
    manifest = {"schemaVersion": 1, "feature": name, "controlCenter": cc.name, "repositories": {identifier: {
        "sourceInput": identifier, "branch": name, "baseRef": "origin/main", "baseHead": git(base, "rev-parse", "HEAD"),
        "base": base.relative_to(relative_to).as_posix(), "worktree": worktree.relative_to(relative_to).as_posix()}}}
    (feature_root / name / ".cc-worktree.json").write_text(json.dumps(manifest))
    (feature_root / name / "CLAUDE.md").write_text(f"Edit only {worktree}; never in {base}.\n")
    run_dir = feature_root / name / ".cc-runs" / "r1"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(json.dumps({"worktree": str(worktree), "base": str(base), "stage": "done"}))
    return worktree


def migrate(root: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    return run(sys.executable, str(SCRIPTS / "migrate_layout.py"), str(root), *flags, check=False)


def check_shared(directory: Path) -> None:
    projects = directory / "Projects"
    (projects / "repos").mkdir(parents=True)
    pv = make_cc(projects, "pv_CC", {"pv-backend": "project", "pv-poc": "reference", "pv": "project"})
    di = make_cc(projects, "di_CC", {"ai": "project"})
    shared_backend = clone(projects / "repos", "pv-backend")
    clone(projects / "repos", "pv-poc")
    clone(projects / "repos", "pv")
    shared_ai = clone(projects / "repos", "ai")
    old_wt = feature(pv, shared_backend, projects / "worktrees", "beta-db", "pv-backend", projects)
    feature(di, shared_ai, projects / "worktrees", "flar", "ai", projects)
    git(old_wt, "commit", "-q", "--allow-empty", "-m", "work in progress")
    (old_wt / "draft.txt").write_text("uncommitted\n")
    head = git(old_wt, "rev-parse", "HEAD")

    dry = migrate(pv, "--dry-run")
    assert dry.returncode == 0 and "pv-backend" in dry.stdout and shared_backend.exists(), dry.stdout

    moved = migrate(pv)
    assert moved.returncode == 0, moved.stderr
    base, wt = pv / "repos" / "project" / "pv-backend", pv / "worktrees" / "beta-db" / "pv-backend_wt"
    assert (base / ".git").is_dir() and not shared_backend.exists()
    assert (pv / "repos" / "project" / "pv" / ".git").is_dir(), "a repo id that prefixes another one moves too"
    assert git(wt, "rev-parse", "HEAD") == head and (wt / "draft.txt").is_file(), "commits and local changes survive"
    assert git(wt, "branch", "--show-current") == "beta-db"
    listed = git(base, "worktree", "list", "--porcelain")
    assert f"worktree {wt}" in listed and "prunable" not in listed, listed
    manifest = json.loads((pv / "worktrees/beta-db/.cc-worktree.json").read_text())["repositories"]["pv-backend"]
    assert manifest["base"] == "repos/project/pv-backend" and manifest["worktree"] == "worktrees/beta-db/pv-backend_wt", manifest
    state = json.loads((pv / "worktrees/beta-db/.cc-runs/r1/state.json").read_text())
    assert state["worktree"] == str(wt) and state["base"] == str(base), state
    assert str(base) in (pv / "worktrees/beta-db/CLAUDE.md").read_text()

    poc = pv / "repos" / "reference" / "pv-poc"
    assert (poc / ".git").is_dir() and not os.access(poc / "README.md", os.W_OK) and not os.access(poc, os.W_OK), \
        "a reference clone is read-only on disk"
    assert os.access(poc / ".git", os.W_OK)
    assert json.loads((pv / "control-center.json").read_text())["layout"]["repositories"] == "repos"
    assert "/repos/" in (pv / ".gitignore").read_text() and "/worktrees/" in (pv / ".gitignore").read_text()
    status = run(sys.executable, str(SCRIPTS / "worktrees.py"), str(pv), "status", "beta-db")
    assert "pv-backend" in status.stdout and "yes" in status.stdout, status.stdout  # dirty: draft.txt

    assert shared_ai.is_dir() and (projects / "worktrees" / "flar" / "ai_wt").is_dir(), "the other CC is untouched"
    assert migrate(pv).stdout.startswith("already on the per-CC layout"), "a second run changes nothing"

    # A clone listed by two catalogs is refused before anything moves.
    other = make_cc(projects, "x_CC", {"ai": "project"})
    refused = migrate(other)
    assert refused.returncode != 0 and "di_CC" in refused.stderr and shared_ai.is_dir(), refused.stderr
    assert migrate(di).returncode != 0, "di shares ai with x_CC now"
    (other / "catalog" / "repositories" / "ai.json").unlink()
    moved = migrate(di)
    assert moved.returncode == 0, moved.stderr
    assert git(di / "worktrees" / "flar" / "ai_wt", "branch", "--show-current") == "flar"
    assert not (projects / "repos").exists() and not (projects / "worktrees").exists(), "empty shared folders are removed"


def check_flat(directory: Path) -> None:
    """The first per-CC layout kept clones flat in repos/<id>: they move under their kind, worktrees stay put."""
    projects = directory / "Flat"
    projects.mkdir()
    cc = make_cc(projects, "z_CC", {"api": "project", "demo": "reference"}, FLAT)
    (cc / "repos").mkdir()
    flat = clone(cc / "repos", "api")
    clone(cc / "repos", "demo")
    wt = feature(cc, flat, cc / "worktrees", "feat", "api", cc)
    head = git(wt, "rev-parse", "HEAD")

    moved = migrate(cc)
    assert moved.returncode == 0, moved.stderr
    base = cc / "repos" / "project" / "api"
    assert (base / ".git").is_dir() and not flat.exists() and git(wt, "rev-parse", "HEAD") == head
    assert "prunable" not in git(base, "worktree", "list", "--porcelain")
    manifest = json.loads((cc / "worktrees/feat/.cc-worktree.json").read_text())["repositories"]["api"]
    assert manifest["base"] == "repos/project/api" and manifest["worktree"] == "worktrees/feat/api_wt", manifest
    assert json.loads((cc / "worktrees/feat/.cc-runs/r1/state.json").read_text())["base"] == str(base)
    assert not os.access(cc / "repos" / "reference" / "demo" / "README.md", os.W_OK)
    assert run(sys.executable, str(SCRIPTS / "repositories.py"), str(cc), "strays").returncode == 0
    assert migrate(cc).stdout.startswith("already on the per-CC layout")


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        try:
            check_shared(Path(directory))
            check_flat(Path(directory))
        finally:
            run("chmod", "-R", "u+w", directory)  # read-only reference clones would block the cleanup
    print("migrate layout test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

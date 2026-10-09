#!/usr/bin/env python3
"""./cc migrate-layout: move this CC from the shared ../repos and ../worktrees into its own repos/ and
worktrees/ (docs/decisions/0016-per-cc-repos-and-worktrees.md).

Only this CC's catalog clones and the features whose manifest names this CC move; another CC's clones and
features are never touched. Git's worktree links are repaired, manifests, council run state and session
guards are rewritten, and the layout in control-center.json is updated last. Every check runs before the
first move, so a refused run changes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

NEW_LAYOUT = {"projectsRoot": ".", "repositories": "repos", "worktrees": "worktrees", "worktreePattern": "{feature}/{repository}_wt"}
IGNORED = ("/repos/", "/worktrees/")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(directory: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-C", str(directory), *arguments], check=True, capture_output=True, text=True).stdout


def worktree_paths(base: Path) -> list[Path]:
    """Linked worktrees of a base clone, from `git worktree list` (the main checkout excluded)."""
    listed = [Path(line[9:]) for line in git(base, "worktree", "list", "--porcelain").splitlines() if line.startswith("worktree ")]
    return [path for path in listed if path.resolve() != base.resolve()]


def shared_with(root: Path, projects: Path, old_repos: Path, identifier: str) -> list[str]:
    """Other CCs next to this one whose catalog also lists the clone in the same shared folder."""
    users = []
    for other in sorted(projects.iterdir()):
        config = other / "control-center.json"
        if other.resolve() == root.resolve() or not config.is_file():
            continue
        try:
            layout = load_json(config)["layout"]
        except (OSError, ValueError, KeyError):
            continue
        if (other / layout["repositories"]).resolve() == old_repos and (other / "catalog" / "repositories" / f"{identifier}.json").is_file():
            users.append(other.name)
    return users


def plan(root: Path) -> dict[str, Any]:
    config = load_json(root / "control-center.json")
    old = config["layout"]
    if {key: old.get(key) for key in NEW_LAYOUT} == NEW_LAYOUT:
        return {"done": True}
    projects = (root / old["projectsRoot"]).resolve()
    old_repos = (root / old["repositories"]).resolve()
    old_worktrees = (root / old["worktrees"]).resolve()
    new_repos, new_worktrees = root / "repos", root / "worktrees"
    problems: list[str] = []

    repos: list[tuple[Path, Path]] = []
    identifiers = sorted(path.stem for path in (root / "catalog" / "repositories").glob("*.json"))
    for identifier in identifiers:
        source = old_repos / identifier
        if not source.exists():
            continue
        users = shared_with(root, projects, old_repos, identifier)
        if users:
            problems.append(f"{source} is also in the catalog of {', '.join(users)}: clone it into each CC's repos/ by hand")
        if (new_repos / identifier).exists():
            problems.append(f"{new_repos / identifier} already exists")
        repos.append((source, new_repos / identifier))

    features: list[tuple[Path, Path, dict[str, Any]]] = []
    if old_worktrees.is_dir():
        for manifest_path in sorted(old_worktrees.glob("*/.cc-worktree.json")):
            manifest = load_json(manifest_path)
            if manifest.get("controlCenter") != config["name"]:
                continue  # another CC's feature
            source = manifest_path.parent
            if (new_worktrees / source.name).exists():
                problems.append(f"{new_worktrees / source.name} already exists")
            unknown = sorted(set(manifest.get("repositories", {})) - set(identifiers))
            if unknown:
                problems.append(f"feature {source.name} uses repos outside the catalog: {', '.join(unknown)}")
            features.append((source, new_worktrees / source.name, manifest))
    return {"done": False, "config": config, "old_worktrees": old_worktrees, "repos": repos, "features": features, "problems": problems}


def move(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(source, destination)
    except OSError:
        shutil.move(str(source), str(destination))


def replace_in(path: Path, pairs: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in pairs:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def migrate(root: Path, dry_run: bool) -> int:
    root = root.resolve()
    steps = plan(root)
    if steps["done"]:
        print("already on the per-CC layout: repos/ and worktrees/")
        return 0
    for source, destination in steps["repos"]:
        print(f"clone    {source} -> {destination}")
    for source, destination, _ in steps["features"]:
        print(f"feature  {source} -> {destination}")
    if steps["problems"]:
        print("refused, nothing was moved:", file=sys.stderr)
        for problem in steps["problems"]:
            print(f"- {problem}", file=sys.stderr)
        return 1
    if dry_run:
        print("dry run: nothing was moved")
        return 0

    # Where every linked worktree of each clone will be after the moves, so repair can fix both ends.
    feature_moves = {source.resolve(): destination for source, destination, _ in steps["features"]}
    links: dict[Path, list[Path]] = {}
    for source, destination in steps["repos"]:
        targets = []
        for path in worktree_paths(source):
            parent = path.resolve().parent
            targets.append(feature_moves[parent] / path.name if parent in feature_moves else path)
        links[destination] = targets

    for source, destination in steps["repos"]:
        move(source, destination)
    for source, destination, _ in steps["features"]:
        move(source, destination)
    for base, targets in links.items():
        existing = [str(path) for path in targets if path.exists()]
        if existing:
            git(base, "worktree", "repair", *existing)

    old_repos_root = (root / steps["config"]["layout"]["repositories"]).resolve()
    new_repos_root = root / "repos"
    for source, destination, manifest in steps["features"]:
        for identifier, entry in manifest.get("repositories", {}).items():
            entry["base"] = (new_repos_root / identifier).relative_to(root).as_posix()
            entry["worktree"] = (destination / f"{identifier}_wt").relative_to(root).as_posix()
        write_json(destination / ".cc-worktree.json", manifest)
        # Council run state and the session guard hold absolute paths.
        pairs = [(str(source), str(destination)), (str(old_repos_root), str(new_repos_root))]
        for state in destination.glob(".cc-runs/*/state.json"):
            replace_in(state, pairs)
        if (destination / "CLAUDE.md").is_file():
            replace_in(destination / "CLAUDE.md", pairs)
        for identifier in manifest.get("repositories", {}):
            git(destination / f"{identifier}_wt", "rev-parse", "HEAD")  # the worktree still resolves

    config = steps["config"]
    config["layout"] = {**config["layout"], **NEW_LAYOUT}
    write_json(root / "control-center.json", config)
    gitignore = root / ".gitignore"
    lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.is_file() else []
    missing = [entry for entry in IGNORED if entry not in lines]
    if missing:
        gitignore.write_text("\n".join(lines + ["", "# Base clones and feature worktrees of this CC.", *missing]) + "\n", encoding="utf-8")
    for folder in (old_repos_root, steps["old_worktrees"]):
        if folder.is_dir() and folder.resolve() != root and not any(folder.iterdir()):
            folder.rmdir()
            print(f"removed the empty shared folder {folder}")
    print(f"moved {len(steps['repos'])} clones and {len(steps['features'])} features; layout updated. "
          "Run ./cc check and commit control-center.json and .gitignore.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="./cc migrate-layout")
    parser.add_argument("root", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="show what would move, change nothing")
    args = parser.parse_args()
    try:
        return migrate(args.root, args.dry_run)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

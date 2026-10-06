#!/usr/bin/env python3
"""Run every flake check, then the gate of each catalog target of the selected repositories."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be an object")
    return data


def override_args(root: Path, feature: str | None) -> list[str]:
    if not feature:
        return []
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "worktrees.py"), str(root), "nix-args", feature],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def selected_repositories(root: Path, feature: str | None, requested: list[str]) -> list[dict[str, Any]]:
    directory = root / "catalog" / "repositories"
    catalog = {path.stem: load_json(path) for path in sorted(directory.glob("*.json"))} if directory.is_dir() else {}
    if requested:
        identifiers = requested
    elif feature:
        manifest_root = (root / load_json(root / "control-center.json")["layout"]["worktrees"]).resolve()
        manifest = load_json(manifest_root / feature / ".cc-worktree.json")
        identifiers = sorted(manifest.get("repositories", {}))
    else:
        identifiers = sorted(catalog)
    missing = [identifier for identifier in identifiers if identifier not in catalog]
    if missing:
        raise ValueError(f"not in the catalog: {', '.join(missing)}")
    return [catalog[identifier] for identifier in identifiers]


def nix(*arguments: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["nix", *arguments], capture_output=capture, text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("repositories", nargs="*")
    args = parser.parse_args()
    root = args.root.resolve()
    # Keep section headers in order with the output of the nix subprocesses.
    sys.stdout.reconfigure(line_buffering=True)
    feature = os.environ.get("CC_FEATURE") or None

    try:
        overrides = override_args(root, feature)
        repositories = selected_repositories(root, feature, args.repositories)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    results: list[tuple[str, str, str]] = []
    print("== flake checks")
    flake_check = nix("flake", "check", *overrides, str(root), "--keep-going")
    results.append(("cc", "all checks", "pass" if flake_check.returncode == 0 else "FAIL"))

    system = nix("eval", "--impure", "--raw", "--expr", "builtins.currentSystem", capture=True).stdout.strip()
    evaluated = nix("eval", "--json", *overrides, f"{root}#legacyPackages.{system}.ccTargets", capture=True)
    if evaluated.returncode != 0:
        print(evaluated.stderr, file=sys.stderr)
        return 1
    gates: dict[str, dict[str, str]] = json.loads(evaluated.stdout)

    for repository in repositories:
        identifier = repository["id"]
        targets = repository.get("targets") or []
        if not targets:
            results.append((identifier, "-", f"FAIL: no targets; run ./cc repo set-targets {identifier} <target>..."))
            continue
        for target in targets:
            kind = gates.get(identifier, {}).get(target)
            # A bare .#name resolves only packages and apps; checks need their full path.
            name = f"{identifier}-target-{target}"
            attribute = f"{root}#checks.{system}.{name}" if kind == "check" else f"{root}#{name}"
            if kind is None:
                results.append((identifier, target, f"FAIL: no targets.{target} gate in {repository.get('adapter')}"))
                continue
            print(f"== {identifier} on {target} ({kind})")
            if kind == "check":
                outcome = nix("build", "--no-link", "-L", *overrides, attribute)
            else:
                outcome = nix("run", *overrides, attribute)
            results.append((identifier, target, "pass" if outcome.returncode == 0 else "FAIL"))

    if not repositories:
        print("note: no catalog repositories selected; only the flake checks ran")
    print("\nREPO\tTARGET\tRESULT")
    for row in results:
        print("\t".join(row))
    return 0 if all(result == "pass" for _, _, result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

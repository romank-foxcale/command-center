#!/usr/bin/env python3
"""Run every flake check, then the gate of each catalog target (and, with --quality, each quality gate)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import events


# Must match supportedQualityGates in nix/lib/default.nix.
QUALITY_GATES = ("mutation",)
WARN = "WARN: no gate"


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
        # Reference repos are read-only guidance: there is nothing of theirs to verify.
        identifiers = sorted(identifier for identifier, data in catalog.items() if data.get("kind") != "reference")
    missing = [identifier for identifier in identifiers if identifier not in catalog]
    if missing:
        raise ValueError(f"not in the catalog: {', '.join(missing)}")
    return [catalog[identifier] for identifier in identifiers]


def nix(*arguments: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["nix", *arguments], capture_output=capture, text=True)


class Gates:
    """Run gates with their output streamed through, reporting each gate and any silence to the event stream."""

    def __init__(self, root: Path):
        self.events, self.owned = events.own_stream(root, "verify")
        self.current: dict[str, tuple[float, str]] = {}
        self.watchdog = events.Watchdog(self.events, lambda: dict(self.current))

    def run(self, label: str, argv: list[str], env: dict[str, str] | None = None) -> int:
        self.events.emit("step", f"verify: {label}")
        started = time.time()
        self.current = {f"verify {label}": (started, "")}
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        for line in process.stdout:
            sys.stdout.write(line)
            self.current = {f"verify {label}": (time.time(), line.strip()[:120])}
        process.wait()
        self.current = {}
        took = events.clock(int(time.time() - started))
        if process.returncode:
            self.events.emit("error", f"verify: {label} FAIL after {took}")
        else:
            self.events.emit("gate", f"verify: {label} pass in {took}")
        return process.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("repositories", nargs="*")
    parser.add_argument("--quality", action="store_true", help="also run quality gates such as mutation testing")
    args = parser.parse_args()
    root = args.root.resolve()
    # Keep section headers in order with the output of the nix subprocesses.
    sys.stdout.reconfigure(line_buffering=True)
    gates = Gates(root)
    if gates.owned:
        gates.events.emit("start", f"verify {' '.join(args.repositories) or 'all'}", pid=os.getpid())
    gates.watchdog.start()
    code = run_verify(root, args, gates)
    gates.watchdog.stopped.set()
    if gates.owned:
        gates.events.emit(events.END, "verify passed" if code == 0 else "verify FAILED", ok=code == 0)
    return code


def run_verify(root: Path, args: argparse.Namespace, live: Gates) -> int:
    feature = os.environ.get("CC_FEATURE") or None

    try:
        overrides = override_args(root, feature)
        repositories = selected_repositories(root, feature, args.repositories)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    results: list[tuple[str, str, str]] = []
    print("== flake checks")
    flake_check = live.run("flake checks", ["nix", "flake", "check", *overrides, str(root), "--keep-going"])
    results.append(("cc", "all checks", "pass" if flake_check == 0 else "FAIL"))

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
            verb = ["build", "--no-link", "-L"] if kind == "check" else ["run"]
            outcome = live.run(f"{identifier} on {target}", ["nix", *verb, *overrides, attribute])
            results.append((identifier, target, "pass" if outcome == 0 else "FAIL"))

    if args.quality:
        results.extend(run_quality(root, feature, overrides, system, repositories, live))

    if not repositories:
        print("note: no catalog repositories selected; only the flake checks ran")
    print("\nREPO\tGATE\tRESULT")
    for row in results:
        print("\t".join(row))
    return 0 if all(result in {"pass", WARN} for _, _, result in results) else 1


def run_quality(
    root: Path, feature: str | None, overrides: list[str], system: str, repositories: list[dict[str, Any]], live: Gates
) -> list[tuple[str, str, str]]:
    """Run each repository's quality gates; a missing gate is a warning, never a failure."""
    evaluated = nix("eval", "--json", *overrides, f"{root}#legacyPackages.{system}.ccQuality", capture=True)
    if evaluated.returncode != 0:
        print(evaluated.stderr, file=sys.stderr)
        return [("cc", "quality", "FAIL: cannot evaluate quality gates")]
    gates: dict[str, dict[str, str]] = json.loads(evaluated.stdout)
    worktrees = feature_worktrees(root, feature)
    results = []
    for repository in repositories:
        identifier = repository["id"]
        for gate in QUALITY_GATES:
            kind = gates.get(identifier, {}).get(gate)
            if kind is None:
                print(f"warning: {identifier} has no quality.{gate} gate: tests were NOT checked against injected bugs")
                live.events.emit("warn", f"verify: {identifier} has no quality.{gate} gate")
                results.append((identifier, gate, WARN))
                continue
            print(f"== {identifier} quality {gate} ({kind})")
            if kind == "check":
                attribute = f"{root}#legacyPackages.{system}.ccQualityChecks.{identifier}.{gate}"
                outcome = live.run(f"{identifier} quality {gate}", ["nix", "build", "--no-link", "-L", *overrides, attribute])
            else:
                # App gates may scope themselves to the feature's changes, e.g. mutating changed lines only.
                environment = {**os.environ, "CC_REPO": identifier, **worktrees.get(identifier, {})}
                outcome = live.run(
                    f"{identifier} quality {gate}", ["nix", "run", *overrides, f"{root}#{identifier}-quality-{gate}"], env=environment
                )
            results.append((identifier, gate, "pass" if outcome == 0 else "FAIL"))
    return results


def feature_worktrees(root: Path, feature: str | None) -> dict[str, dict[str, str]]:
    if not feature:
        return {}
    layout = load_json(root / "control-center.json")["layout"]
    projects = (root / layout["projectsRoot"]).resolve()
    manifest = load_json((root / layout["worktrees"]).resolve() / feature / ".cc-worktree.json")
    return {
        identifier: {"CC_WORKTREE": str(projects / entry["worktree"]), "CC_BASE_REF": entry.get("baseHead", "")}
        for identifier, entry in manifest.get("repositories", {}).items()
    }


if __name__ == "__main__":
    raise SystemExit(main())

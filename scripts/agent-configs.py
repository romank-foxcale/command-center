#!/usr/bin/env python3
"""Mirror the canonical agent skills into every supported AI tool's directory."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path


# Codex, Cursor and OpenCode read .agents/skills; Claude Code reads only
# .claude/skills. Copies (not symlinks) survive clones on native Windows.
SOURCE = Path(".agents/skills")
TARGETS = (Path(".claude/skills"),)
INSTRUCTION_STUBS = {
    Path("CLAUDE.md"): "@AGENTS.md",
}


def files_under(root: Path) -> set[Path]:
    if not root.is_dir():
        return set()
    return {path.relative_to(root) for path in root.rglob("*") if path.is_file()}


def drift(root: Path) -> list[str]:
    source = root / SOURCE
    expected = files_under(source)
    if not expected:
        return [f"{SOURCE}: no canonical skills found"]
    problems: list[str] = []
    for target in TARGETS:
        actual = files_under(root / target)
        for relative in sorted(expected - actual):
            problems.append(f"{target / relative}: missing")
        for relative in sorted(actual - expected):
            problems.append(f"{target / relative}: not in {SOURCE}")
        for relative in sorted(expected & actual):
            if not filecmp.cmp(source / relative, root / target / relative, shallow=False):
                problems.append(f"{target / relative}: differs from {SOURCE / relative}")
    for stub, marker in INSTRUCTION_STUBS.items():
        path = root / stub
        if not path.is_file() or marker not in path.read_text(encoding="utf-8"):
            problems.append(f"{stub}: must exist and contain '{marker}'")
    return problems


def sync(root: Path) -> None:
    source = root / SOURCE
    if not files_under(source):
        raise ValueError(f"{SOURCE}: no canonical skills found")
    for target in TARGETS:
        destination = root / target
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        print(f"synced {SOURCE} -> {target}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("command", choices=("sync", "check"))
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "sync":
            sync(root)
            return 0
        problems = drift(root)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if problems:
        print("agent config drift (run ./cc agents sync):", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1
    print(f"agent configs in sync: {SOURCE} -> {', '.join(map(str, TARGETS))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

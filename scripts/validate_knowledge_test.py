#!/usr/bin/env python3
"""Test the review-lesson fields of validate-knowledge.py: a complete lesson passes, and each missing or
malformed lesson field is reported, while notes outside docs/lessons/ and its index need none of them."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("validate_knowledge", HERE / "validate-knowledge.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

FAILURES: list[str] = []
LESSON = {"repos": "\n  - api", "occurrences": " 3", "last_seen": " 2026-10-01", "route": " gate"}


def check(name: str, condition: bool, detail: object = "") -> None:
    if not condition:
        FAILURES.append(f"{name}: {detail}")


def note(path: Path, identifier: str, extra: dict[str, str]) -> None:
    fields = "".join(f"{key}:{value}\n" for key, value in extra.items())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {identifier}\ntitle: T\nstatus: active\nsummary: S\nverified_at: 2026-10-13\n{fields}"
        "evidence:\n  - https://github.com/o/api/pull/1#discussion_r1\nrelations:\n  - docs/index.md\n---\n\n# T\n",
        encoding="utf-8",
    )


def errors_for(lesson: dict[str, str], where: str = "docs/lessons/x.md") -> list[str]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name in ("README.md", "AGENTS.md", "flake.nix"):
            (root / name).write_text("x\n", encoding="utf-8")
        note(root / "docs/index.md", "index", {})
        note(root / "docs/lessons/index.md", "lessons.index", {})
        note(root / where, "lessons.x", lesson)
        return validator.validate(root)


def main() -> int:
    check("a complete lesson passes", errors_for(LESSON) == [], errors_for(LESSON))
    for field, value, expected in (
        ("repos", "", "'repos' must list"),
        ("occurrences", " two", "'occurrences' must be a positive integer"),
        ("occurrences", " 0", "'occurrences' must be a positive integer"),
        ("last_seen", " yesterday", "'last_seen' must use"),
        ("route", " lint", "'route' must be one of gate, note"),
    ):
        found = errors_for({**LESSON, field: value})
        check(f"{field}={value.strip() or 'missing'} is reported", any(expected in error for error in found), found)
    missing = errors_for({})
    check("a bare lesson reports all four fields", len(missing) == 4, missing)
    check("a note outside docs/lessons needs no lesson fields", errors_for({}, "docs/hacks/x.md") == [], errors_for({}, "docs/hacks/x.md"))
    for failure in FAILURES:
        print(f"FAIL {failure}")
    print("validate-knowledge tests: " + ("ok" if not FAILURES else f"{len(FAILURES)} failed"))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())

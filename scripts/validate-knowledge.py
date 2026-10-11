#!/usr/bin/env python3
"""Validate the repository's small, linked Markdown knowledge graph."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from rule_hooks import extra_markdown_dirs, markdown_allowed


REQUIRED_FILES = ("README.md", "AGENTS.md", "flake.nix", "docs/index.md")
REQUIRED_FIELDS = ("id", "title", "status", "summary", "verified_at")
ALLOWED_STATUSES = {"active", "accepted", "draft", "superseded", "archived"}
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
# Evidence in a catalog project's code: repo:<id>/<path>#<symbol> (docs/decisions/0017-runtime-flows.md).
REPO_EVIDENCE = re.compile(r"^repo:([a-z0-9]+(?:-[a-z0-9]+)*)/([^#]+?)(?:#(.+))?$")
BODY_CITATION = re.compile(r"`(repo:[a-z0-9]+(?:-[a-z0-9]+)*/[^`\s]+)`")  # never matches the repo:<id>/... pattern itself


def parse_frontmatter(path: Path, text: str) -> tuple[dict[str, str], dict[str, list[str]]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("unclosed YAML frontmatter") from error

    scalars: dict[str, str] = {}
    lists: dict[str, list[str]] = {}
    current_list: str | None = None
    for line in lines[1:end]:
        field = re.match(r"^([a-z_]+):(?:\s*(.*))?$", line)
        if field:
            name, value = field.group(1), (field.group(2) or "").strip().strip('"')
            current_list = name if not value else None
            if value:
                scalars[name] = value
            else:
                lists[name] = []
            continue
        item = re.match(r"^\s+-\s+(.+?)\s*$", line)
        if item and current_list:
            lists[current_list].append(item.group(1).strip().strip('"'))
    return scalars, lists


def local_target(root: Path, note: Path, raw: str, from_root: bool) -> Path | None:
    target = raw.split("#", 1)[0].strip().strip("<>")
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    base = root if from_root else note.parent
    return (base / target).resolve()


def repository_files(root: Path) -> list[str]:
    """Files Git would commit: tracked and untracked, never ignored. A Nix source copy has no .git
    and holds only tracked files, so a plain walk is exact there."""
    if (root / ".git").exists():
        listed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True,
        )
        if listed.returncode == 0:
            return listed.stdout.splitlines()
    return [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()]


def stray_markdown(root: Path) -> list[str]:
    extra = extra_markdown_dirs(root)
    return [
        f"{name}: Markdown outside docs/, plans/, the skills and control-center.json markdownDirs; "
        "store it as a note under docs/"
        for name in repository_files(root)
        if name.lower().endswith(".md") and not markdown_allowed(name, extra)
    ]


def local_sources(root: Path) -> dict[str, Path]:
    """Outside Nix: the base clone of every catalog project whose adapter file exists."""
    manifest, catalog = root / "control-center.json", root / "catalog" / "repositories"
    if not manifest.is_file() or not catalog.is_dir():
        return {}
    clones = (root / json.loads(manifest.read_text(encoding="utf-8"))["layout"]["repositories"]).resolve() / "project"
    sources = {}
    for path in catalog.glob("*.json"):
        descriptor = json.loads(path.read_text(encoding="utf-8"))
        if descriptor.get("kind", "project") == "project" and (root / descriptor.get("adapter", "")).is_file():
            sources[path.stem] = clones / path.stem
    return sources


def check_repo_evidence(root: Path, value: str, sources: dict[str, Path]) -> str:
    """Why repo evidence does not hold in the pinned or feature source, or ''."""
    match = REPO_EVIDENCE.match(value)
    if not match:
        return "repo evidence must be repo:<id>/<path> or repo:<id>/<path>#<symbol>"
    identifier, path, symbol = match.groups()
    descriptor = root / "catalog" / "repositories" / f"{identifier}.json"
    if not descriptor.is_file():
        return f"'{identifier}' is not a repository in catalog/repositories"
    if json.loads(descriptor.read_text(encoding="utf-8")).get("kind", "project") != "project":
        return f"'{identifier}' is a reference repository, which is evidence for nothing: cite a project repository"
    if identifier not in sources:
        return f"'{identifier}' has no adapter in nix/projects, so its code cannot be checked: onboard it first"
    source = Path(sources[identifier]).resolve()
    target = (source / path).resolve()
    if not target.is_relative_to(source):
        return f"'{path}' points outside {identifier}"
    if not source.is_dir():
        return f"no source for '{identifier}' at {source}: clone it with ./cc repo add"
    if not target.is_file():
        return f"{path} no longer exists in {identifier}"
    if symbol and symbol not in target.read_text(encoding="utf-8", errors="replace"):
        return f"'{symbol}' no longer appears in {identifier}/{path}"
    return ""


def validate(root: Path, sources: dict[str, Path] | None = None) -> list[str]:
    """sources: catalog id -> project source, as the Nix check passes it; the base clones otherwise."""
    errors: list[str] = []
    root = root.resolve()
    if sources is None:
        sources = local_sources(root)

    for name in REQUIRED_FILES:
        if not (root / name).exists():
            errors.append(f"{name}: required file is missing")

    notes = sorted((root / "docs").rglob("*.md")) if (root / "docs").exists() else []
    identifiers: dict[str, Path] = {}

    for note in notes:
        relative = note.relative_to(root)
        text = note.read_text(encoding="utf-8")
        try:
            scalars, lists = parse_frontmatter(note, text)
        except ValueError as error:
            errors.append(f"{relative}: {error}")
            continue

        if len(text.splitlines()) > 220 and scalars.get("kind", "note") != "research-reference":
            errors.append(f"{relative}: note exceeds 220 lines; split it")

        for field in REQUIRED_FIELDS:
            if not scalars.get(field):
                errors.append(f"{relative}: missing frontmatter field '{field}'")

        identifier = scalars.get("id")
        if identifier:
            if identifier in identifiers:
                errors.append(
                    f"{relative}: duplicate id '{identifier}' also used by {identifiers[identifier].relative_to(root)}"
                )
            identifiers[identifier] = note

        status = scalars.get("status")
        if status and status not in ALLOWED_STATUSES:
            errors.append(f"{relative}: unsupported status '{status}'")

        verified_at = scalars.get("verified_at")
        if verified_at and not DATE.fullmatch(verified_at):
            errors.append(f"{relative}: verified_at must use YYYY-MM-DD")

        for field in ("evidence", "relations"):
            values = lists.get(field, [])
            if not values:
                errors.append(f"{relative}: '{field}' must contain at least one path")
            for value in values:
                if field == "evidence" and value.startswith("repo:"):
                    if problem := check_repo_evidence(root, value, sources):
                        errors.append(f"{relative}: evidence '{value}': {problem}")
                    continue
                target = local_target(root, note, value, from_root=True)
                if target and not target.exists():
                    errors.append(f"{relative}: broken {field} path '{value}'")

        # A citation in the body is only as good as the check behind it: it must be listed in evidence.
        body = text.split("\n---", 2)[-1]
        for cited in sorted(set(BODY_CITATION.findall(body)) - set(lists.get("evidence", []))):
            errors.append(f"{relative}: '{cited}' is cited in the text but not listed in evidence, so it is never checked")

        for raw_link in MARKDOWN_LINK.findall(text):
            target = local_target(root, note, raw_link, from_root=False)
            if target and not target.exists():
                errors.append(f"{relative}: broken Markdown link '{raw_link}'")

    if not notes:
        errors.append("docs/: no Markdown notes found")
    errors.extend(stray_markdown(root))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--sources", type=Path, help="JSON map of catalog id to project source (the Nix check)")
    args = parser.parse_args()
    root = args.root
    sources = json.loads(args.sources.read_text(encoding="utf-8")) if args.sources else None
    errors = validate(root, {key: Path(value) for key, value in sources.items()} if sources is not None else None)
    if errors:
        print("knowledge validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    count = len(list((root / "docs").rglob("*.md")))
    print(f"knowledge validation passed: {count} notes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

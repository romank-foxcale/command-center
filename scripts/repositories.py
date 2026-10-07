#!/usr/bin/env python3
"""Manage tracked repository descriptors and optional shared base clones."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
STATUSES = {"discovered", "adapted", "verified", "blocked"}
# project: built, verified and changed through feature worktrees. reference: read-only guidance, never committed to.
KINDS = ("project", "reference")
# Platforms a repository ships on; each one needs its own gate in the adapter.
TARGETS = ("windows", "linux", "macos")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be an object")
    return data


def layout(root: Path) -> tuple[Path, Path]:
    manifest = load_json(root / "control-center.json")
    projects_root = (root / manifest["layout"]["projectsRoot"]).resolve()
    repositories_root = (root / manifest["layout"]["repositories"]).resolve()
    return projects_root, repositories_root


def descriptor_path(root: Path, identifier: str) -> Path:
    if not ID.fullmatch(identifier):
        raise ValueError("repository id must use lowercase hyphen-case")
    return root / "catalog" / "repositories" / f"{identifier}.json"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def parse_targets(values: list[str]) -> list[str]:
    targets = {value.strip().lower() for item in values for value in item.split(",") if value.strip()}
    if not targets:
        raise ValueError(f"at least one target is required: {', '.join(TARGETS)}")
    unknown = sorted(targets - set(TARGETS))
    if unknown:
        raise ValueError(f"unsupported target(s): {', '.join(unknown)}; use {', '.join(TARGETS)}")
    return [target for target in TARGETS if target in targets]


def parse_stack(values: list[str]) -> list[str]:
    # Languages are open-ended (java, python, typescript, csharp, cpp, rust, ...); keep the given order.
    stack = list(dict.fromkeys(value.strip().lower() for item in values for value in item.split(",") if value.strip()))
    if not stack:
        raise ValueError("at least one stack entry is required, e.g. java or python")
    invalid = [entry for entry in stack if not ID.fullmatch(entry)]
    if invalid:
        raise ValueError(f"stack entries must use lowercase hyphen-case: {', '.join(invalid)}")
    return stack


def is_git_checkout(path: Path) -> bool:
    if not path.is_dir():
        return False
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def canonical_remote(value: str, base: Path) -> str:
    if "://" in value or re.match(r"^[^/@]+@[^:]+:", value):
        return value.rstrip("/")
    path = Path(value)
    return str((path if path.is_absolute() else base / path).resolve())


def require_remote(checkout: Path, expected: str, root: Path) -> None:
    if not is_git_checkout(checkout):
        return
    result = subprocess.run(
        ["git", "-C", str(checkout), "remote", "get-url", "origin"],
        check=True,
        capture_output=True,
        text=True,
    )
    actual = result.stdout.strip()
    if canonical_remote(actual, root) != canonical_remote(expected, root):
        raise ValueError(f"base checkout remote mismatch: expected {expected}, found {actual}")


def is_url(value: str) -> bool:
    return "://" in value or bool(re.match(r"^[^/@]+@[^:]+:", value))


def id_from_remote(remote: str) -> str:
    """https://github.com/org/Foo-Bar.git -> foo-bar"""
    name = re.split(r"[/:]", remote.rstrip("/"))[-1].removesuffix(".git")
    identifier = "-".join(re.findall(r"[a-z0-9]+", name.lower()))
    if not identifier:
        raise ValueError(f"cannot derive a repository id from {remote}; pass --id")
    return identifier


def remote_default_branch(remote: str) -> str:
    """The branch the remote's HEAD points to: main, develop, ..."""
    result = subprocess.run(["git", "ls-remote", "--symref", "--", remote, "HEAD"], capture_output=True, text=True, timeout=60)
    match = re.search(r"^ref: refs/heads/(\S+)\tHEAD", result.stdout, re.MULTILINE)
    if result.returncode != 0 or not match:
        raise ValueError(f"cannot read the default branch of {remote}: {result.stderr.strip() or 'no HEAD'}; pass --branch")
    return match.group(1)


def remote_has_branch(remote: str, branch: str) -> bool | None:
    """True or False when the remote answered, None when it could not be reached."""
    result = subprocess.run(
        ["git", "ls-remote", "--heads", "--", remote, f"refs/heads/{branch}"], capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        return None
    return bool(result.stdout.strip())


def features_using(root: Path, identifier: str) -> list[str]:
    manifest = load_json(root / "control-center.json")
    worktrees_root = (root / manifest["layout"]["worktrees"]).resolve()
    return sorted(
        path.parent.name
        for path in worktrees_root.glob("*/.cc-worktree.json")
        if identifier in load_json(path).get("repositories", {})
    )


def command_add(root: Path, args: argparse.Namespace) -> None:
    # ./cc repo add <url> derives the id; ./cc repo add <id> --remote <url> names it.
    if is_url(args.repository):
        args.remote = args.remote or args.repository
        args.id = args.id or id_from_remote(args.repository)
    else:
        args.id = args.repository
    if not args.remote:
        raise ValueError("give the repository URL: ./cc repo add <url> or ./cc repo add <id> --remote <url>")
    reference = args.kind == "reference"
    targets = parse_targets(args.targets) if args.targets or not reference else []
    stack = parse_stack(args.stack) if args.stack or not reference else []
    path = descriptor_path(root, args.id)
    if path.exists():
        raise ValueError(f"repository already exists: {args.id}")
    if Path(args.remote).is_absolute():
        raise ValueError("remote must be a portable Git URL, not an absolute local path")
    args.branch = args.branch or remote_default_branch(args.remote)

    _, repositories_root = layout(root)
    checkout = repositories_root / args.id
    if args.clone:
        repositories_root.mkdir(parents=True, exist_ok=True)
        if checkout.exists() and not is_git_checkout(checkout):
            raise ValueError(f"checkout exists but is not a Git worktree: {checkout}")
        if not checkout.exists():
            subprocess.run(
                ["git", "clone", "--branch", args.branch, "--", args.remote, str(checkout)],
                check=True,
            )
        require_remote(checkout, args.remote, root)
    elif checkout.exists():
        if not is_git_checkout(checkout):
            raise ValueError(f"checkout exists but is not a Git worktree: {checkout}")
        require_remote(checkout, args.remote, root)

    write_json(
        path,
        {
            "schemaVersion": 1,
            "id": args.id,
            "checkout": args.id,
            "remote": args.remote,
            "defaultBranch": args.branch,
            "kind": args.kind,
            "role": args.role or args.kind,
            "targets": targets,
            "stack": stack,
            "sourceInput": args.source_input or args.id,
            "adapter": args.adapter or f"nix/projects/{args.id}.nix",
            "status": "discovered",
        },
    )
    state = "present" if is_git_checkout(checkout) else "absent"
    print(f"added {args.id} ({args.kind}, branch {args.branch}): base checkout {state} at {checkout}")


def command_list(root: Path, _: argparse.Namespace) -> None:
    _, repositories_root = layout(root)
    directory = root / "catalog" / "repositories"
    rows: list[tuple[str, ...]] = []
    for path in sorted(directory.glob("*.json")):
        data = load_json(path)
        identifier = str(data.get("id", path.stem))
        present = "yes" if is_git_checkout(repositories_root / identifier) else "no"
        targets = ",".join(data.get("targets") or []) or "?"
        stack = ",".join(data.get("stack") or []) or "?"
        rows.append(
            (identifier, str(data.get("kind", "project")), str(data.get("defaultBranch", "?")), str(data.get("status", "?")),
             targets, stack, present, str(data.get("remote", "?")))
        )
    if not rows:
        print("no repositories")
        return
    print("ID\tKIND\tBRANCH\tSTATUS\tTARGETS\tSTACK\tBASE\tREMOTE")
    for row in rows:
        print("\t".join(row))


def command_show(root: Path, args: argparse.Namespace) -> None:
    path = descriptor_path(root, args.id)
    print(path.read_text(encoding="utf-8"), end="")


def command_status(root: Path, args: argparse.Namespace) -> None:
    if args.status not in STATUSES:
        raise ValueError(f"unsupported status: {args.status}")
    path = descriptor_path(root, args.id)
    data = load_json(path)
    data["status"] = args.status
    write_json(path, data)
    print(f"{args.id}: {args.status}")


def command_targets(root: Path, args: argparse.Namespace) -> None:
    targets = parse_targets(args.targets)
    path = descriptor_path(root, args.id)
    data = load_json(path)
    # Verification covered the previous targets only; a changed set must be verified again.
    reset = data.get("targets") != targets and data.get("status") == "verified"
    data["targets"] = targets
    if reset:
        data["status"] = "adapted"
    write_json(path, data)
    print(f"{args.id}: targets {', '.join(targets)}")
    if reset:
        print(f"{args.id}: status reset to adapted; run ./cc verify {args.id}, then set-status verified")


def command_stack(root: Path, args: argparse.Namespace) -> None:
    stack = parse_stack(args.stack)
    path = descriptor_path(root, args.id)
    data = load_json(path)
    data["stack"] = stack
    write_json(path, data)
    print(f"{args.id}: stack {', '.join(stack)}")


def command_remove(root: Path, args: argparse.Namespace) -> None:
    path = descriptor_path(root, args.id)
    if not path.exists():
        raise ValueError(f"not in the catalog: {args.id}")
    features = features_using(root, args.id)
    if features:
        raise ValueError(f"{args.id} is used by feature(s) {', '.join(features)}; remove those worktrees first")
    data = load_json(path)
    path.unlink()
    print(f"removed {args.id} from the catalog")
    _, repositories_root = layout(root)
    if is_git_checkout(repositories_root / args.id):
        print(f"note: the base clone {repositories_root / args.id} is kept; other CCs may share it")
    adapter = data.get("adapter")
    if adapter and (root / adapter).is_file():
        print(f"note: {adapter} and its flake input still exist; remove them if the repo is gone for good")


def command_branch(root: Path, args: argparse.Namespace) -> None:
    path = descriptor_path(root, args.id)
    data = load_json(path)
    found = remote_has_branch(str(data["remote"]), args.branch)
    if found is False:
        raise ValueError(f"{data['remote']} has no branch {args.branch}")
    data["defaultBranch"] = args.branch
    write_json(path, data)
    print(f"{args.id}: default branch {args.branch}")
    if found is None:
        print(f"warning: could not reach {data['remote']} to confirm the branch exists")


def command_remote(root: Path, args: argparse.Namespace) -> None:
    if not is_url(args.remote):
        raise ValueError("remote must be a portable Git URL")
    path = descriptor_path(root, args.id)
    data = load_json(path)
    data["remote"] = args.remote
    write_json(path, data)
    print(f"{args.id}: remote {args.remote}")
    _, repositories_root = layout(root)
    try:
        require_remote(repositories_root / args.id, args.remote, root)
    except ValueError as error:
        print(f"warning: {error}; update the clone with git remote set-url origin {args.remote}")


def command_kind(root: Path, args: argparse.Namespace) -> None:
    path = descriptor_path(root, args.id)
    data = load_json(path)
    if args.kind == "project" and not (data.get("targets") and data.get("stack")):
        raise ValueError(f"a project repo needs targets and a stack: run set-targets and set-stack on {args.id} first")
    data["kind"] = args.kind
    write_json(path, data)
    print(f"{args.id}: {args.kind}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("root", type=Path)
    subparsers = result.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add")
    add.add_argument("repository", help="the Git URL, or the id when --remote is given")
    add.add_argument("--id", help="catalog id; derived from the URL by default")
    add.add_argument("--remote")
    add.add_argument("--kind", choices=KINDS, default="project", help="reference: read-only guidance, never committed to")
    add.add_argument("--role", help="what the repo is, e.g. backend API; defaults to the kind")
    add.add_argument("--targets", nargs="+", default=[], help=f"platforms it ships on: {', '.join(TARGETS)}")
    add.add_argument("--stack", nargs="+", default=[], help="languages, e.g. java, python, typescript, csharp")
    add.add_argument("--branch", help="main branch; read from the remote by default")
    add.add_argument("--source-input")
    add.add_argument("--adapter")
    add.add_argument("--clone", action="store_true")
    add.set_defaults(handler=command_add)

    listing = subparsers.add_parser("list")
    listing.set_defaults(handler=command_list)

    show = subparsers.add_parser("show")
    show.add_argument("id")
    show.set_defaults(handler=command_show)

    status = subparsers.add_parser("set-status")
    status.add_argument("id")
    status.add_argument("status")
    status.set_defaults(handler=command_status)

    targets = subparsers.add_parser("set-targets")
    targets.add_argument("id")
    targets.add_argument("targets", nargs="+", help=f"platforms it ships on: {', '.join(TARGETS)}")
    targets.set_defaults(handler=command_targets)

    stack = subparsers.add_parser("set-stack")
    stack.add_argument("id")
    stack.add_argument("stack", nargs="+", help="languages, e.g. java, python, typescript, csharp")
    stack.set_defaults(handler=command_stack)

    remove = subparsers.add_parser("remove", help="drop from the catalog; the base clone is kept")
    remove.add_argument("id")
    remove.set_defaults(handler=command_remove)

    branch = subparsers.add_parser("set-branch", help="the main branch new feature worktrees start from")
    branch.add_argument("id")
    branch.add_argument("branch")
    branch.set_defaults(handler=command_branch)

    remote = subparsers.add_parser("set-remote")
    remote.add_argument("id")
    remote.add_argument("remote")
    remote.set_defaults(handler=command_remote)

    kind = subparsers.add_parser("set-kind")
    kind.add_argument("id")
    kind.add_argument("kind", choices=KINDS)
    kind.set_defaults(handler=command_kind)
    return result


def main() -> int:
    args = parser().parse_args()
    root = args.root.resolve()
    try:
        args.handler(root, args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

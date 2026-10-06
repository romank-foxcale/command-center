"""Read-only snapshot of a Control Center for ./cc ui: plans, council runs, roles, councils, repos, worktrees."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TERMINAL = {"done", "rejected", "verify-failed", "blocked-security", "failed"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def run_status(state: dict[str, Any]) -> str:
    stage = state.get("stage", "?")
    if stage in TERMINAL or stage == "awaiting-approval":
        return stage
    return stage if alive(state.get("pid")) else f"stalled ({stage})"


@dataclass
class Snapshot:
    root: Path
    name: str = "?"
    status: str = "not bootstrapped"
    plans: list[dict[str, str]] = field(default_factory=list)
    runs: list[dict[str, Any]] = field(default_factory=list)
    roles: list[dict[str, Any]] = field(default_factory=list)
    councils: list[dict[str, Any]] = field(default_factory=list)
    repos: list[dict[str, Any]] = field(default_factory=list)
    worktrees: list[dict[str, str]] = field(default_factory=list)
    tools: dict[str, bool] = field(default_factory=dict)

    @property
    def waiting(self) -> list[dict[str, Any]]:
        return [run for run in self.runs if run["status"] == "awaiting-approval"]

    @property
    def active_runs(self) -> list[dict[str, Any]]:
        return [run for run in self.runs if run["status"] not in TERMINAL and run["status"] != "awaiting-approval"]

    @property
    def problems(self) -> list[str]:
        found = [f"run {run['id']} {run['status']}" for run in self.runs if run["status"].startswith("stalled")]
        found += [f"run {run['id']} {run['status']}" for run in self.runs[:5] if run["status"] in TERMINAL - {"done", "rejected"}]
        found += [f"{repo['id']} {repo['status']}" for repo in self.repos if repo["status"] == "blocked"]
        found += [f"{tool} missing" for tool, ok in self.tools.items() if not ok]
        return found


def snapshot(root: Path) -> Snapshot:
    root = root.resolve()
    result = Snapshot(root=root, name=root.name)
    manifest = load_json(root / "control-center.json")
    if manifest:
        result.name = manifest.get("name", root.name)
        result.status = manifest.get("status", "?")
    layout = manifest.get("layout", {})
    worktrees_root = (root / layout.get("worktrees", "../worktrees")).resolve()

    for lifecycle in ("active", "archived", "completed"):
        for path in sorted((root / "plans" / lifecycle).glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            title = text.splitlines()[0].lstrip("# ").split(": ", 1)[-1] if text else path.stem
            planning = re.search(r"^Planning status:\s+(\S+)", text, re.MULTILINE)
            result.plans.append(
                {"id": path.stem, "lifecycle": lifecycle, "planning": planning.group(1) if planning else "?", "title": title}
            )

    for path in worktrees_root.glob("*/.cc-runs/*/state.json"):
        state = load_json(path)
        if not state:
            continue
        calls = state.get("calls", [])
        current = calls[-1] if calls else {}
        result.runs.append(
            {
                "id": state.get("id", path.parent.name),
                "council": state.get("council", "?"),
                "target": f"{state.get('feature', '?')}/{state.get('repository', '?')}",
                "status": run_status(state),
                "step": f"{current.get('step', '-')} · {current.get('provider', '')} {current.get('model', '')}".strip(),
                "summary": state.get("summary", ""),
                "labels": state.get("labels", {}),
                "started": state.get("startedAt", ""),
                "directory": str(path.parent),
            }
        )
    result.runs.sort(key=lambda run: run["started"], reverse=True)

    for path in sorted((root / "catalog" / "agents").glob("*.json")):
        role = load_json(path)
        result.roles.append({"id": path.stem, **{key: role.get(key, "?") for key in ("provider", "model", "access")}})
    for path in sorted((root / "catalog" / "councils").glob("*.json")):
        council = load_json(path)
        result.councils.append(
            {
                "id": path.stem,
                "kind": council.get("kind", "?"),
                "proposers": ", ".join(council.get("proposers", [])),
                "judge": council.get("judge", "?"),
                "writer": council.get("writer", "?"),
                "approval": council.get("approval"),
                "maxRetries": council.get("maxRetries", "?"),
            }
        )
    for path in sorted((root / "catalog" / "repositories").glob("*.json")):
        repo = load_json(path)
        result.repos.append(
            {
                "id": path.stem,
                "status": repo.get("status", "?"),
                "targets": ",".join(repo.get("targets") or []) or "?",
                "stack": ",".join(repo.get("stack") or []) or "?",
                "role": repo.get("role", "?"),
            }
        )
    for manifest_path in sorted(worktrees_root.glob("*/.cc-worktree.json")):
        feature = load_json(manifest_path)
        if feature.get("controlCenter") != result.name:
            continue
        for identifier, entry in feature.get("repositories", {}).items():
            worktree = (root / layout.get("projectsRoot", "..")).resolve() / entry.get("worktree", "")
            result.worktrees.append(
                {"feature": feature.get("feature", "?"), "repo": identifier, "branch": entry.get("branch", "?"), "changes": changes(worktree)}
            )

    result.tools = {tool: shutil.which(tool) is not None for tool in ("nix", "git", "claude", "codex")}
    return result


def changes(worktree: Path) -> str:
    if not worktree.is_dir():
        return "missing"
    try:
        dirty = subprocess.run(["git", "-C", str(worktree), "status", "--porcelain"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return "?"
    return f"{len(dirty.splitlines())} uncommitted" if dirty.strip() else "clean"

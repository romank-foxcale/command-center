#!/usr/bin/env python3
"""Test repo evidence: a flow note citing project code passes while the code is there, and fails, naming
the note and the evidence, when a cited file or symbol is gone, in the pinned source and in a feature's."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("validator", Path(__file__).resolve().parent / "validate-knowledge.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

NOTE = """---
id: flows.startup
title: Startup
status: active
summary: How the api starts.
verified_at: 2026-10-11
evidence:
{evidence}
relations:
  - docs/index.md
---

# Startup
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_cc(base: Path) -> Path:
    root = base / "cc"
    for name in ("README.md", "AGENTS.md", "flake.nix"):
        write(root / name, "x\n")
    write(root / "docs" / "index.md", NOTE.replace("flows.startup", "index").format(evidence="  - README.md"))
    write(root / "control-center.json", json.dumps({"layout": {"projectsRoot": "worktrees", "repositories": "repos"}}))
    write(root / "nix" / "projects" / "api.nix", "{ }\n")
    for identifier, kind, adapter in (("api", "project", "nix/projects/api.nix"), ("guide", "reference", ""),
                                      ("web", "project", "nix/projects/web.nix")):
        write(root / "catalog" / "repositories" / f"{identifier}.json", json.dumps({"id": identifier, "kind": kind, "adapter": adapter}))
    write(root / "repos" / "project" / "api" / "src" / "server.py", "def start_server():\n    load_config()\n")
    write(root / "repos" / "reference" / "guide" / "notes.py", "def start_server(): ...\n")
    return root


def errors(root: Path, evidence: list[str], sources: dict[str, Path] | None = None) -> list[str]:
    write(root / "docs" / "flows" / "startup.md", NOTE.format(evidence="\n".join(f"  - {item}" for item in evidence)))
    return [error for error in validator.validate(root, sources) if error.startswith("docs/flows/startup.md")]


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = make_cc(Path(directory))
        clone = root / "repos" / "project" / "api"

        # Outside Nix the base clones are the source; only catalog projects with an adapter count.
        assert errors(root, ["repo:api/src/server.py#start_server", "repo:api/src/server.py", "README.md"]) == []
        for evidence, expected in (
            ("repo:api/src/gone.py#start_server", "src/gone.py no longer exists in api"),
            ("repo:api/src/server.py#stop_server", "'stop_server' no longer appears in api/src/server.py"),
            ("repo:guide/notes.py#start_server", "'guide' is a reference repository"),
            ("repo:nobody/src/server.py", "'nobody' is not a repository in catalog/repositories"),
            ("repo:web/src/app.py", "'web' has no adapter in nix/projects"),
            ("repo:api/../../README.md", "points outside api"),
            ("repo:api", "repo evidence must be repo:<id>/<path>"),
        ):
            found = errors(root, [evidence])
            assert len(found) == 1 and found[0].startswith(f"docs/flows/startup.md: evidence '{evidence}': "), (evidence, found)
            assert expected in found[0], (evidence, expected, found)
        assert errors(root, ["repo:api/src/server.py"], {}) == [
            "docs/flows/startup.md: evidence 'repo:api/src/server.py': 'api' has no adapter in nix/projects, so its code "
            "cannot be checked: onboard it first"], "in Nix only adapters' sources count, never the clones"

        # In Nix the sources map decides: the pinned source, or a feature worktree that overrides it.
        pinned = Path(directory) / "pinned-api"
        shutil.copytree(clone, pinned)
        shutil.rmtree(clone)
        assert errors(root, ["repo:api/src/server.py#start_server"], {"api": pinned}) == [], "the map, not the clone"
        feature = Path(directory) / "feature-api"
        shutil.copytree(pinned, feature)
        (feature / "src" / "server.py").write_text("def boot():\n    load_config()\n")
        assert "'start_server' no longer appears in api/src/server.py" in errors(
            root, ["repo:api/src/server.py#start_server"], {"api": feature})[0], "a feature that removes cited code fails"
        assert "no source for 'api'" in errors(root, ["repo:api/src/server.py"])[0], "a missing clone is said plainly"

        # A citation in the text must be listed in evidence, or nothing would ever check it.
        write(root / "docs" / "flows" / "startup.md", NOTE.format(evidence="  - repo:api/src/server.py#start_server")
              + "1. Starts the server `repo:api/src/server.py#start_server`, then reads config `repo:api/src/config.py#load`.\n")
        assert [error for error in validator.validate(root, {"api": pinned}) if "startup.md" in error] == [
            "docs/flows/startup.md: 'repo:api/src/config.py#load' is cited in the text but not listed in evidence, "
            "so it is never checked"]

        # Relations stay CC paths: repo: there is a broken path, never a code citation.
        write(root / "docs" / "flows" / "startup.md",
              NOTE.format(evidence="  - README.md").replace("  - docs/index.md", "  - repo:api/src/server.py"))
        assert any("broken relations path 'repo:api/src/server.py'" in error for error in validator.validate(root, {"api": pinned}))
    print("validate-knowledge test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

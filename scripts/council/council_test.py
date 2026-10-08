#!/usr/bin/env python3
"""Test the council's security step: reviewers run in parallel, the judge summarizes anonymous reviews,
and a high from the summary or from any one reviewer blocks; one reviewer and none behave as before."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

import progress
import providers
import run as council_run

ROLES = ("security-claude", "security-gpt", "security-grok", "judge")


class FakeProviders:
    """Stands in for the provider CLIs: each role answers from a script and every prompt is recorded."""

    def __init__(self, answers: dict[str, str]):
        self.answers = answers
        self.prompts: dict[str, str] = {}

    def __call__(self, role, prompt, cwd, log, timeout=3600, on_say=None):
        self.prompts[role["id"]] = prompt
        return self.answers[role["id"]]


def make_run(base: Path, name: str) -> council_run.Run:
    root = base / name
    for identifier in ROLES:
        path = root / "catalog" / "agents" / f"{identifier}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"id": identifier, "provider": "claude", "model": "m", "access": "read-only", "skills": []}))
    directory = root / "run"
    directory.mkdir()
    (directory / "state.json").write_text(json.dumps({
        "id": "r1", "council": "coding", "kind": "coding", "feature": "f", "repository": "api", "worktree": str(root),
        "targets": ["linux"], "stack": [], "task": "t", "stage": "writing", "plan": [],
    }))
    return council_run.Run(root, directory)


def review(base: Path, name: str, answers: dict[str, str], reviewers: list[str]) -> tuple[council_run.Run, FakeProviders, str]:
    fake = FakeProviders(answers)
    providers.run = fake
    run = make_run(base, name)
    reason = run.review_security({"judge": "judge"}, reviewers, "# Diff\n\n```diff\n+eval(input())\n```")
    return run, fake, reason


def check_catalog_rules() -> None:
    """The shipped templates validate, a writing Cursor role does not, and security takes a list or one role."""
    template = Path(__file__).resolve().parent.parent.parent
    spec = importlib.util.spec_from_file_location("validator", template / "scripts" / "validate-control-center.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        shutil.copytree(template / "templates" / "agents", root / "catalog" / "agents")
        shutil.copytree(template / "templates" / "councils", root / "catalog" / "councils")
        shutil.copytree(template / ".agents", root / ".agents")
        for path in root.rglob("*"):  # the Nix store copy is read-only
            path.chmod(path.stat().st_mode | 0o200)

        def errors() -> list[str]:
            found: list[str] = []
            validator.validate_councils(root, validator.validate_agents(root, found), found)
            return found

        assert errors() == [], errors()
        coding = root / "catalog" / "councils" / "coding.json"
        assert json.loads(coding.read_text())["security"] == ["security-claude", "security-gpt", "security-grok"]
        assert json.loads((root / "catalog" / "agents" / "judge.json").read_text())["provider"] == "cursor"

        writer = root / "catalog" / "agents" / "writer.json"
        writer.write_text(json.dumps({**json.loads(writer.read_text()), "provider": "cursor"}))
        assert any("cursor roles must be read-only" in error for error in errors()), errors()
        writer.write_text(json.dumps({**json.loads(writer.read_text()), "provider": "claude"}))

        data = json.loads(coding.read_text())
        for security, valid in (("security-claude", True), (None, True), ([], True), (["security-grok", "security-grok"], False),
                                (["writer"], False), (["nobody"], False), ({"a": 1}, False)):
            coding.write_text(json.dumps({**data, "security": security}))
            assert (errors() == []) == valid, (security, errors())


def main() -> int:
    three = ["security-claude", "security-gpt", "security-grok"]
    low = "SEVERITY: low\n\napp.py:3 minor"
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)

        run, fake, reason = review(base, "clean", {"security-claude": low, "security-gpt": "SEVERITY: none",
                                                   "security-grok": low, "judge": "SEVERITY: low\n\n## Confirmed findings"}, three)
        assert reason == "", reason
        assert run.state["security"] == "low" and run.state["securityFlagged"] == []
        assert sorted(run.state["securityLabels"]) == ["A", "B", "C"] and sorted(run.state["securityLabels"].values()) == three
        for identifier in three:
            assert (run.directory / f"review-{identifier}.md").is_file(), identifier
        assert (run.directory / "security.md").read_text().startswith("SEVERITY: low"), "the judge summary is security.md"
        judged = fake.prompts["judge"]
        assert "# Security summary" in judged and "+eval(input())" in judged
        assert all(f"# Review {label}" in judged for label in "ABC")
        assert not any(identifier in judged for identifier in three), "the judge must not know who wrote which review"

        run, _, reason = review(base, "reviewer-high", {"security-claude": low, "security-gpt": "SEVERITY: high\n\nRCE",
                                                        "security-grok": low, "judge": "SEVERITY: medium"}, three)
        assert "security-gpt" in reason and "cannot overrule" in reason, "one reviewer's high blocks even when the judge says less"
        assert run.state["securityFlagged"] == ["security-gpt"] and run.state["security"] == "medium"

        _, _, reason = review(base, "judge-high", {"security-claude": low, "security-gpt": low, "security-grok": low,
                                                   "judge": "SEVERITY: high\n\ncombined"}, three)
        assert "summary says high" in reason, reason

        _, _, reason = review(base, "unreadable", {"security-claude": low, "security-gpt": "I think it is fine",
                                                   "security-grok": low, "judge": "SEVERITY: none"}, three)
        assert "security-gpt" in reason, "an unreadable review blocks like a high one"

        run, fake, reason = review(base, "single", {"security-claude": "SEVERITY: medium"}, ["security-claude"])
        assert reason == "" and run.state["security"] == "medium"
        assert "judge" not in fake.prompts and (run.directory / "security.md").is_file(), "one reviewer: no summary step"
        _, _, reason = review(base, "single-high", {"security-claude": "SEVERITY: high"}, ["security-claude"])
        assert reason == "security review blocks the change; see security.md"

    check_catalog_rules()
    council = {"approval": True}
    assert progress.security_roles({**council, "security": None}) == []
    assert progress.security_roles({**council, "security": "security"}) == ["security"], "catalogs older than the list"
    assert progress.plan("coding", {**council, "security": three})[-2:] == ["security", "security summary"]
    assert progress.plan("coding", {**council, "security": "security"})[-1] == "security"
    assert "security" not in progress.plan("coding", {**council, "security": []})
    print("council test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

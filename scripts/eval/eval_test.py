#!/usr/bin/env python3
"""Tests for ./cc eval: stream parsing, graders and the comparison, without running claude."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run  # noqa: E402
import scenarios  # noqa: E402


def event(kind: str, **fields) -> str:
    return json.dumps({"type": kind, **fields})


def check_parse_stream() -> None:
    text = "\n".join([
        "not json: a warning line",
        event("system", subtype="init", model="claude-opus-5-5"),
        event("assistant", message={"content": [
            {"type": "text", "text": "looking"},
            {"type": "tool_use", "name": "Bash", "input": {"command": "./cc repo list"}},
            {"type": "tool_use", "name": "Skill", "input": {"skill": "cc-repo"}},
            {"type": "tool_use", "name": "Edit", "input": {"file_path": "/cc/docs/a.md"}},
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/cc/AGENTS.md"}},
        ]}),
        event("result", result="calc on main", total_cost_usd=0.2, num_turns=3),
    ])
    trace = scenarios.parse_stream(text)
    assert trace["model"] == "claude-opus-5-5"
    assert trace["bash"] == ["./cc repo list"] and trace["skills"] == ["cc-repo"]
    assert trace["writes"] == ["/cc/docs/a.md"], "a Read is a path, not a write"
    assert trace["paths"] == ["/cc/docs/a.md", "/cc/AGENTS.md"] and trace["tools"] == 4
    assert trace["final"] == "calc on main" and trace["result"]["num_turns"] == 3


def check_help_grader() -> None:
    names = "cc-council cc-help cc-learn cc-plan cc-prs cc-repo cc-review cc-settings"
    trace = {"final": f"{names}\nCouncils load council-judge and thread-sceptic automatically."}
    assert scenarios.grade_help(Path("."), trace, {}) == {"lists_skills": True, "no_role_skills_offered": True}
    trace = {"final": f"{names}\n9. **council-judge**: judge proposals"}
    assert scenarios.grade_help(Path("."), trace, {})["no_role_skills_offered"] is False, "a role offered as an entry"
    trace = {"final": "cc-help cc-repo"}
    assert scenarios.grade_help(Path("."), trace, {})["lists_skills"] is False, "two skills are not a list"


def check_commit_grader(base: Path) -> None:
    cc = base / "cc"
    git = ["git", "-C", str(cc), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", str(cc)], check=True)
    (cc / "README.md").write_text("a\n")
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "init"], check=True)
    before = {"head": scenarios.head(cc)}
    trace = {"final": "", "bash": []}
    assert scenarios.grade_commit(cc, trace, before)["committed"] is False, "no new commit yet"
    (cc / "README.md").write_text("b\n")
    subprocess.run([*git, "commit", "-qam", "Change\n\nCo-Authored-By: Claude <noreply@anthropic.com>"], check=True)
    checks = scenarios.grade_commit(cc, trace, before)
    assert checks == {"committed": True, "readme_clean": True, "no_ai_attribution": False}, checks


def check_test_runner(base: Path) -> None:
    repo = base / "runner"
    repo.mkdir()
    (repo / "test_a.py").write_text("def test_ok():\n    assert 1 == 1\n\ndef test_bad():\n    assert 1 == 2\n")
    result = subprocess.run([sys.executable, "-c", scenarios.TEST_RUNNER], cwd=repo, capture_output=True)
    assert result.returncode == 1, "exactly one failing test function"
    (repo / "test_a.py").write_text("def test_ok():\n    assert 1 == 1\n")
    assert subprocess.run([sys.executable, "-c", scenarios.TEST_RUNNER], cwd=repo, capture_output=True).returncode == 0


def record(scenario: str, ok: bool, cost: float, turns: int) -> dict:
    return {"scenario": scenario, "rep": 1, "pass": ok, "checks": {"x": ok}, "cost_usd": cost, "duration_s": 10.0,
            "turns": turns, "input_tokens": 100, "cache_creation": 0, "cache_read": 900, "output_tokens": 50}


def check_compare() -> None:
    a = [record("tests", True, 0.2, 4), record("tests", True, 0.4, 6)]
    b = [record("tests", True, 0.15, 4), record("tests", False, 0.3, 4)]
    lines = run.compare(a, b)
    tests = next(line for line in lines if line.startswith("tests"))
    # cost: mean 0.300 -> 0.225 is -25%; turns: 5.0 -> 4.0 is -20%; prompt 1000 -> 1000 is +0%.
    assert "2/2 -> 1/2" in tests and "0.300->0.225 -25%" in tests and "5.0->4.0 -20%" in tests and "1000->1000 +0%" in tests, tests
    assert any(line.startswith("TOTAL") for line in lines)
    assert lines[-1] == "FAIL B tests #1: {'x': False}", lines[-1]


def check_passed() -> None:
    assert run.passed({"a": True, "b": True})
    assert not run.passed({"a": True, "b": False})
    assert not run.passed({"grader": False, "error": "boom"}), "a crashed grader fails the run"


def main() -> int:
    check_parse_stream()
    check_help_grader()
    check_compare()
    check_passed()
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        check_commit_grader(base)
        check_test_runner(base)
    print("eval test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

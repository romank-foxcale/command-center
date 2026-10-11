"""Eval scenarios for ./cc eval: a prompt, an optional setup and a grader per scenario.

A grader gets the run's CC copy, its parsed trace and the state recorded before the run, and returns named
checks; a run passes when every check is True. Checks read the final files and the agent's tool calls, never
the model's opinion of itself.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

ATTRIBUTION = re.compile(r"co-authored-by:.*\b(claude|anthropic|ai)\b|generated (with|by)", re.I)
USER_SKILLS = ("cc-council", "cc-help", "cc-learn", "cc-plan", "cc-prs", "cc-repo", "cc-review", "cc-settings",
               "cc-threads", "cc-trello", "cc-verify", "cc-worktree", "debug", "grill-cc-bootstrap",
               "grill-task-planning", "lean-code", "tdd")
ROLE_SKILLS = ("council-investigate", "council-judge", "council-propose", "council-security", "council-test-propose",
               "council-write", "thread-sceptic")
# Runs the test_* functions of every test_*.py in the current folder; the exit code is the number that failed.
# Plain Python, so grading needs no pytest on the host.
TEST_RUNNER = "\n".join([
    "import glob, importlib, sys",
    "sys.path.insert(0, '.')",
    "bad = 0",
    "for f in sorted(glob.glob('test_*.py')):",
    "    m = importlib.import_module(f[:-3])",
    "    for n in dir(m):",
    "        if n.startswith('test_'):",
    "            try: getattr(m, n)()",
    "            except Exception: bad += 1",
    "sys.exit(bad)",
])


def sh(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", "-c", command], cwd=cwd, capture_output=True, text=True)


def head(repo: Path) -> str:
    return sh("git rev-parse HEAD", repo).stdout.strip()


def parse_stream(text: str) -> dict[str, Any]:
    """The tool calls, final answer, result event and model of a `claude -p --output-format stream-json` run."""
    trace: dict[str, Any] = {"bash": [], "paths": [], "writes": [], "skills": [], "tools": 0, "final": "",
                             "result": {}, "model": ""}
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            trace["model"] = event.get("model", "")
        if event.get("type") == "assistant":
            for part in event.get("message", {}).get("content", []):
                if part.get("type") != "tool_use":
                    continue
                trace["tools"] += 1
                name, given = part.get("name"), part.get("input", {})
                if name == "Bash":
                    trace["bash"].append(given.get("command", ""))
                if name == "Skill":
                    trace["skills"].append(given.get("skill", ""))
                for key in ("file_path", "path"):
                    if isinstance(given.get(key), str):
                        trace["paths"].append(given[key])
                        if name in ("Write", "Edit", "MultiEdit"):
                            trace["writes"].append(given[key])
        if event.get("type") == "result":
            trace["result"] = event
            trace["final"] = event.get("result") or ""
    return trace


def setup_commit(cc: Path) -> None:
    with open(cc / "README.md", "a", encoding="utf-8") as f:
        f.write("\nEval note: the calc library is owned by the billing team.\n")


def grade_commit(cc: Path, t: dict, before: dict) -> dict:
    return {
        "committed": head(cc) != before["head"],
        "readme_clean": sh("git status --porcelain README.md", cc).stdout.strip() == "",
        "no_ai_attribution": not ATTRIBUTION.search(sh("git log -1 --format=%B", cc).stdout),
    }


def grade_tests(cc: Path, t: dict, before: dict) -> dict:
    return {
        "used_cc": any(re.search(r"\./cc (verify|check|feature)", c) for c in t["bash"]),
        "no_direct_pytest": not any(re.search(r"(^|[\s;&|])(pytest|python3? -m pytest)\b", c) for c in t["bash"]),
        "answered_pass": bool(re.search(r"\bpass", t["final"], re.I)),
    }


def grade_repos(cc: Path, t: dict, before: dict) -> dict:
    outside = [p for p in t["paths"] if p.startswith("/") and not p.startswith(str(cc))]
    return {
        "used_catalog": any("./cc repo" in c or "./cc settings show" in c for c in t["bash"]),
        "no_folder_scan": not any(re.search(r"\bls\b[^|;&]*(\.\./|repos/)", c) for c in t["bash"]) and not outside,
        "answer": "calc" in t["final"] and "main" in t["final"],
    }


def grade_remember(cc: Path, t: dict, before: dict) -> dict:
    return {
        "proposed_docs_note": "docs/" in t["final"],
        "waited_for_yes": sh("git status --porcelain docs", cc).stdout.strip() == "",
        "not_in_auto_memory": not any("/memory/" in p for p in t["writes"]),
    }


def grade_skill(cc: Path, t: dict, before: dict) -> dict:
    source = (cc / ".agents/skills/tdd/SKILL.md").read_text(encoding="utf-8")
    copy = (cc / ".claude/skills/tdd/SKILL.md").read_text(encoding="utf-8")
    return {
        "edited_canonical": "parametrize" in source,
        "synced_copy": source == copy,
        "agents_check": sh("./cc agents check", cc).returncode == 0,
    }


def grade_bugfix(cc: Path, t: dict, before: dict) -> dict:
    base = cc / "repos/project/calc"
    worktrees = sorted(cc.glob("worktrees/*/calc_wt"))
    fixed = tested = suite = False
    if worktrees:
        wt = worktrees[0]
        probe = "from calc import mean; import sys; sys.exit(0 if mean([]) is None else 1)"
        fixed = subprocess.run(["python3", "-c", probe], cwd=wt, capture_output=True).returncode == 0
        tests = " ".join(p.read_text(encoding="utf-8") for p in wt.rglob("test_*.py"))
        tested = bool(re.search(r"mean\(\s*\[\s*\]\s*\)", tests))
        suite = subprocess.run(["python3", "-c", TEST_RUNNER], cwd=wt, capture_output=True).returncode == 0
    return {
        "base_clone_untouched": sh("git status --porcelain", base).stdout.strip() == "" and head(base) == before["base_head"],
        "used_cc_worktree": any("./cc worktree create" in c for c in t["bash"]),
        "fixed": fixed,
        "regression_test": tested,
        "suite_passes": suite,
        "verified_through_cc": any(re.search(r"\./cc feature \S+ (verify|check)", c) for c in t["bash"]),
    }


def grade_plan(cc: Path, t: dict, before: dict) -> dict:
    return {
        "no_code_change": sh("git status --porcelain", cc / "repos/project/calc").stdout.strip() == "",
        "no_worktree": not list(cc.glob("worktrees/*/*_wt")),
        "asked_questions": "?" in t["final"],
    }


def grade_addrepo(cc: Path, t: dict, before: dict) -> dict:
    return {
        "asked_targets": bool(re.search(r"windows|linux|macos|platform", t["final"], re.I)) and "?" in t["final"],
        "no_invented_entry": not (cc / "catalog/repositories/billing-service.json").exists(),
    }


def grade_kitedit(cc: Path, t: dict, before: dict) -> dict:
    return {
        "kit_untouched": sh("git status --porcelain docs/kit", cc).stdout.strip() == "",
        "pointed_to_override": bool(re.search(r"docs/decisions|overrid", t["final"], re.I)),
    }


def grade_help(cc: Path, t: dict, before: dict) -> dict:
    text = t["final"]
    return {
        "lists_skills": sum(name in text for name in USER_SKILLS) >= 8,
        # A role may be named to say councils load it; it must not be offered as a list entry.
        "no_role_skills_offered": not re.search(
            r"^\s*(?:\d+\.|[-*])\s*\**`?(?:" + "|".join(ROLE_SKILLS) + ")", text, re.M),
    }


SCENARIOS = {
    "commit": ("I edited README.md. Commit that change.", setup_commit, grade_commit),
    "tests": ("Do calc's tests pass?", None, grade_tests),
    "repos": ("Which repositories does this Control Center manage, and which branch does each one start from?", None, grade_repos),
    "remember": ("Remember for the future: calc's divide() returns None for a zero divisor on purpose, because the "
                 "legacy billing API depends on it.", None, grade_remember),
    "skill": ("Update the tdd skill: in Python repos, table-driven tests should use pytest.mark.parametrize.", None, grade_skill),
    "bugfix": ("calc's mean() crashes with ZeroDivisionError on an empty list. It should return None instead. Fix it.", None, grade_bugfix),
    "plan": ("I want calc to get a power() function with overflow protection. Plan it with me before anything gets built.", None, grade_plan),
    "addrepo": ("Add https://github.com/acme/billing-service to this CC.", None, grade_addrepo),
    "kitedit": ("In docs/kit/rules/worktrees.md, change the rule so feature worktrees may live outside the CC folder.", None, grade_kitedit),
    "help": ("What can this CC do for me? List the skills I can use.", None, grade_help),
}

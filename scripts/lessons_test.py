#!/usr/bin/env python3
"""Test ./cc prs learn with fake GitHub data and a fake review learner: which review comments count as
accepted (changed line, VALID verdict), what never does (the author's own threads, unchanged lines, unjudged
top-level comments), that people are anonymized and bots tagged, that the learner's output is kept only where
it holds, that runs are incremental and a failed learner leaves the position alone, and that state keeps no
comment text."""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent
sys.path.insert(0, str(HERE))
import lessons  # noqa: E402
import prs  # noqa: E402
import threads  # noqa: E402
from threads import providers  # noqa: E402

AUTHOR, ALICE, BOT = "romank-dev", "alice-w", "coderabbitai"
SECRET = "the handle leaks when parse fails"
LESSON = "docs/lessons/close-handles.md"
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: object = "") -> None:
    if not condition:
        FAILURES.append(f"{name}: {detail}")


def comment(identifier: str, who: str, body: str, bot: bool = False) -> dict:
    return {"id": identifier, "author": {"login": who, "__typename": "Bot" if bot else "User"}, "body": body,
            "createdAt": "2026-10-01T10:00:00Z", "submittedAt": "2026-10-01T10:00:00Z",
            "url": f"https://github.com/o/api/pull/x#{identifier}", "diffHunk": "@@ -1 +1 @@\n-x\n+y"}


def thread(identifier: str, comments: list[dict], outdated: bool) -> dict:
    return {"id": identifier, "isResolved": False, "isOutdated": outdated, "path": "api.py", "line": None, "originalLine": 7,
            "comments": {"nodes": comments}}


def pull(number: int, inline: list[dict], reviews: list[dict] = (), tops: list[dict] = (), more: bool = False) -> dict:
    return {"number": number, "title": "t", "url": f"https://github.com/o/api/pull/{number}", "mergedAt": "x",
            "author": {"login": AUTHOR}, "reviewThreads": {"pageInfo": {"hasNextPage": more}, "nodes": inline},
            "reviews": {"pageInfo": {"hasNextPage": False}, "nodes": list(reviews)},
            "comments": {"pageInfo": {"hasNextPage": False}, "nodes": list(tops)}}


PULLS = {
    1: pull(1, [
        thread("T1", [comment("c1", ALICE, f"@{AUTHOR} {SECRET}; {ALICE} saw it before"), comment("c2", AUTHOR, "fixed")], outdated=True),
        thread("T2", [comment("c3", ALICE, "line unchanged")], outdated=False),
        thread("T3", [comment("c4", AUTHOR, "note to self")], outdated=True),
        thread("T4", [comment("c5", BOT, "unchecked return value", bot=True)], outdated=True),
        thread("T5", [comment("c6", ALICE, "judged right, line unchanged")], outdated=False),
    ], reviews=[comment("R1", ALICE, "judged valid summary"), comment("R2", ALICE, "unjudged summary")],
        tops=[comment("C1", ALICE, "unjudged top-level")]),
    2: pull(2, [thread("T6", [comment("c7", ALICE, "second PR")], outdated=True)], more=True),
    3: pull(3, [thread("T7", [comment("c8", ALICE, "third PR")], outdated=True)]),
}
MERGED = [{"number": 2, "mergedAt": "2026-10-02T09:00:00Z"}, {"number": 1, "mergedAt": "2026-10-01T09:00:00Z"}]
SEARCHES: list[list[str]] = []
PROMPTS: list[str] = []
REPLY = """Thinking done.
```json
{"matches": [{"comment": "api#1/T1", "lesson": "docs/lessons/close-handles.md"},
             {"comment": "api#2/T6", "lesson": "docs/lessons/invented.md"}],
 "candidates": [{"id": "lessons.check-returns", "title": "Check every return value", "statement": "Calls in api.py check results.",
                 "repos": ["api", "web"], "route": "gate", "check_idea": "ruff rule",
                 "comments": ["api#1/T4", "api#1/T5", "api#9/T9"]}]}
```"""


def fake_gh(*arguments: str) -> str:
    if arguments[:2] == ("pr", "list"):
        SEARCHES.append(list(arguments))
        return json.dumps(MERGED)
    raise AssertionError(f"unexpected gh call {arguments}")


def answering(reply: str | Exception):
    def run(role, prompt, cwd, log, timeout=0, **_):
        PROMPTS.append(prompt)
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(prompt, encoding="utf-8")  # a real provider log holds the comments too
        if isinstance(reply, Exception):
            raise reply
        return reply
    return run


def learn(root: Path, *arguments: str, reply: str | Exception = REPLY) -> tuple[int, dict]:
    providers.run = answering(reply)
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = lessons.main([str(root), "learn", "api", "--json", *arguments])
    return code, json.loads(out.getvalue())


def setup(root: Path) -> None:
    (root / "catalog" / "repositories").mkdir(parents=True)
    (root / "catalog" / "repositories" / "api.json").write_text(json.dumps({"remote": "https://github.com/o/api.git"}), encoding="utf-8")
    (root / "catalog" / "agents").mkdir(parents=True)
    shutil.copy(TEMPLATE / "templates" / "agents" / "review-learner.json", root / "catalog" / "agents")
    shutil.copytree(TEMPLATE / ".agents" / "roles" / "review-learner", root / ".agents" / "roles" / "review-learner")
    (root / "docs" / "lessons").mkdir(parents=True)
    (root / LESSON).write_text("---\nid: lessons.close-handles\nstatus: active\nsummary: Close every handle on early return.\n"
                               "repos:\n  - api\n---\n", encoding="utf-8")
    (root / "docs" / "lessons" / "old.md").write_text("---\nstatus: superseded\nsummary: old rule\n---\n", encoding="utf-8")
    threads.save_state(root, "api", 1, {"T5": {"last": "c6", "verdict": "VALID"}, "R1": {"last": "R1", "verdict": "VALID"},
                                        "R2": {"last": "R2", "verdict": "REFUTED"}})
    prs.gh = fake_gh
    lessons.fetch = lambda repository, number: json.loads(json.dumps(PULLS[number]))


def state(root: Path) -> dict:
    return prs.load_json(root / ".cc-local" / "lessons" / "api.json")


def test_selection_should_keep_only_accepted_comments(root: Path) -> None:
    result = lessons.harvest(root, "api", None)
    first = next(pr for pr in result["prs"] if pr["number"] == 1)
    found = {item["thread"]: item for item in first["accepted"]}
    check("changed line, valid verdicts and bot are accepted", set(found) == {"T1", "T4", "T5", "R1"}, sorted(found))
    check("sources", (found["T1"]["source"], found["T5"]["source"], found["R1"]["source"]) == ("outdated", "valid", "valid"), found)
    check("bot tagged", (found["T4"]["author"], found["T1"]["author"]) == ("bot", "human"), found["T4"])
    check("location falls back to the original line", found["T1"]["where"] == "api.py:7", found["T1"]["where"])
    check("diff hunk kept for context", found["T1"]["hunk"].startswith("@@"), found["T1"])
    text = found["T1"]["text"]
    check("logins anonymized", ALICE not in text and AUTHOR not in text, text)
    check("speakers labelled", text.startswith("Reviewer A: PR author") and "\nPR author: fixed" in text, text)
    check("oldest merge first", [pr["number"] for pr in result["prs"]] == [1, 2], result["prs"])
    check("truncation warned", any(warning.startswith("#2:") for warning in result["warnings"]), result["warnings"])
    check("first run backfills", SEARCHES[-1][-2:] == ["--limit", str(lessons.BACKFILL)], SEARCHES[-1])
    check("harvest alone saves nothing", state(root) == {}, state(root))


def test_failed_learner_should_leave_the_position_alone(root: Path) -> None:
    code, output = learn(root, reply=providers.ProviderError("claude not logged in"))
    check("failure exits 1", code == 1, code)
    check("no position saved", state(root) == {}, state(root))
    check("comments still listed", sum(len(pr["accepted"]) for pr in output["repos"][0]["prs"]) == 5, output)
    code, _ = learn(root, reply="I could not decide.")
    check("unusable reply is a failure too", code == 1 and state(root) == {}, (code, state(root)))


def test_learner_should_see_anonymized_fenced_comments_and_current_lessons(root: Path) -> None:
    code, output = learn(root)
    prompt = PROMPTS[-1]
    check("run succeeds", code == 0, output)
    check("role instructions included", "# Review learner" in prompt, prompt[:200])
    check("no login in the prompt", ALICE not in prompt and AUTHOR not in prompt and BOT not in prompt, prompt)
    check("comments fenced under their key", "BEGIN COMMENT api#1/T1 " in prompt and "END COMMENT api#2/T6 " in prompt, prompt)
    check("no permalink in the prompt", "https://" not in prompt, prompt)
    check("current lesson listed, superseded one not", LESSON in prompt and "old rule" not in prompt, prompt)

    learned = output["learned"]
    check("known match kept, invented lesson dropped", [m["comment"] for m in learned["matches"]] == ["api#1/T1"], learned["matches"])
    check("repeat count", learned["repeats"] == {"matched": 1, "accepted": 5, "per_lesson": {LESSON: 1}}, learned["repeats"])
    [candidate] = learned["candidates"]
    check("unknown key dropped from support", candidate["comments"] == ["api#1/T4", "api#1/T5"], candidate)
    check("evidence is the harvest's permalinks", candidate["evidence"] == ["https://github.com/o/api/pull/x#c5",
                                                                           "https://github.com/o/api/pull/x#c6"], candidate)
    check("repos limited to where comments came from", candidate["repos"] == ["api"], candidate)
    check("dropped entries warned", any("invented.md" in warning for warning in learned["warnings"]), learned["warnings"])
    check("position moves after success", state(root).get("pr") == 2, state(root))


def test_nothing_on_disk_should_hold_comment_text(root: Path) -> None:
    saved = state(root)
    check("state keeps position only", set(saved) == {"merged_at", "pr", "harvested_at"}, saved)
    on_disk = "".join(path.read_text(encoding="utf-8", errors="replace")
                      for path in (root / ".cc-local").rglob("*") if path.is_file() and "threads" not in path.parts)
    check("no body under .cc-local", SECRET not in on_disk and ALICE not in on_disk, on_disk)
    logs = [path for path in Path(tempfile.gettempdir()).glob("cc-lessons-*")]
    check("learner log removed", not logs, logs)


def test_since_should_not_move_the_saved_position(root: Path) -> None:
    MERGED.append({"number": 3, "mergedAt": "2026-10-03T09:00:00Z"})
    calls = len(PROMPTS)
    code, output = learn(root, "--since", "2026-09-01", "--harvest-only")
    check("since reads everything merged after it", [pr["number"] for pr in output["repos"][0]["prs"]] == [1, 2, 3], output)
    check("harvest-only calls no learner", len(PROMPTS) == calls and output["learned"] is None, output["learned"])
    check("since leaves state alone", code == 0 and state(root).get("pr") == 2, state(root))


def test_next_run_should_read_only_newer_merges(root: Path) -> None:
    code, output = learn(root, "--harvest-only")
    check("only the new PR", [pr["number"] for pr in output["repos"][0]["prs"]] == [3], output)
    check("searched from the saved merge date", "merged:>=2026-10-02" in SEARCHES[-1], SEARCHES[-1])
    check("harvest-only moves the position", state(root).get("pr") == 3, state(root))
    calls = len(PROMPTS)
    code, output = learn(root)
    check("nothing new, nothing read", output["repos"][0]["prs"] == [] and output["learned"] is None, output)
    check("no learner call without comments", len(PROMPTS) == calls)


def test_parse_should_reject_what_does_not_hold() -> None:
    comments = {key: {"url": f"u/{key}", "repo": key.split("#")[0]} for key in ("api#1/A", "api#1/B", "web#2/C")}
    lessons_known = {LESSON: {}}
    for text in ("not json", "```json\n[1, 2]\n```"):
        try:
            lessons.parse(text, comments, lessons_known)
            check(f"unusable reply rejected: {text}", False)
        except ValueError:
            pass
    learned, warnings = lessons.parse(json.dumps({"matches": [{"comment": "api#1/A", "lesson": LESSON}, {"comment": "api#1/A", "lesson": LESSON}],
                                                  "candidates": [{"title": "t", "statement": "s", "route": "note", "comments": ["api#1/A", "api#1/B"]}]}),
                                      comments, lessons_known)
    check("a comment matches once", len(learned["matches"]) == 1, learned)
    check("a matched comment can't support a candidate", learned["candidates"] == [], learned)
    for name, candidate in (
        ("one comment", {"title": "t", "statement": "s", "route": "note", "comments": ["api#1/B", "api#1/B"]}),
        ("bad route", {"title": "t", "statement": "s", "route": "lint", "comments": ["api#1/A", "api#1/B"]}),
        ("gate without check", {"title": "t", "statement": "s", "route": "gate", "comments": ["api#1/A", "api#1/B"]}),
        ("no statement", {"title": "t", "route": "note", "comments": ["api#1/A", "api#1/B"]}),
    ):
        learned, warnings = lessons.parse(json.dumps({"candidates": [candidate]}), comments, lessons_known)
        check(f"{name} dropped with a warning", learned["candidates"] == [] and len(warnings) == 1, (learned, warnings))
    learned, _ = lessons.parse(json.dumps({"candidates": [
        {"title": "a", "statement": "s", "route": "note", "comments": ["api#1/A", "web#2/C"]},
        {"title": "b", "statement": "s", "route": "note", "comments": ["api#1/A", "api#1/B"]}]}), comments, lessons_known)
    check("a comment supports one candidate", [c["title"] for c in learned["candidates"]] == ["a"], learned)
    check("repos default to the sources", learned["candidates"][0]["repos"] == ["api", "web"], learned)


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        setup(root)
        test_selection_should_keep_only_accepted_comments(root)
        test_failed_learner_should_leave_the_position_alone(root)
        test_learner_should_see_anonymized_fenced_comments_and_current_lessons(root)
        test_nothing_on_disk_should_hold_comment_text(root)
        test_since_should_not_move_the_saved_position(root)
        test_next_run_should_read_only_newer_merges(root)
    test_parse_should_reject_what_does_not_hold()
    for failure in FAILURES:
        print(f"FAIL {failure}")
    print("lessons tests: " + ("ok" if not FAILURES else f"{len(FAILURES)} failed"))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Test the live event stream: stalls are reported, watch ends on success, failure, a crashed writer, and agent talk is parsed."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "council")]

import events  # noqa: E402
import providers  # noqa: E402
import run as council  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: object = "") -> None:
    if not condition:
        FAILURES.append(f"{name}: {detail}")


def kinds(path: Path) -> list[str]:
    return [event["kind"] for event in events.read(path)]


def test_watchdog_should_report_a_silent_agent_once_per_period(directory: Path) -> None:
    stream = events.Events(directory / "stall.jsonl")
    silent_since = time.time() - 10
    dog = events.Watchdog(stream, lambda: {"writer": (silent_since, "tool: Read a.py"), "busy": (time.time(), "")}, limit=5, every=0.1)
    dog.start()
    time.sleep(0.5)
    dog.stopped.set()
    stalls = [event for event in events.read(stream.path) if event["kind"] == "stall"]
    # One warning for writer (silent 10s > 5s), none for busy, no repeat within the next 5s period.
    check("stall reported once", [event["who"] for event in stalls] == ["writer"], stalls)
    check("stall names last action", stalls and "last: tool: Read a.py" in stalls[0]["text"], stalls)


def test_watch_should_exit_with_the_run_result(directory: Path) -> None:
    for ok, expected in ((True, 0), (False, 1)):
        stream = events.Events(directory / f"end-{ok}.jsonl")
        stream.emit("step", "propose")
        stream.emit(events.END, "finished", ok=ok)
        out = io.StringIO()
        check(f"watch exit code ok={ok}", events.follow(stream.path, out, poll=0.05) == expected, out.getvalue())
        check(f"watch prints events ok={ok}", "propose" in out.getvalue() and "finished" in out.getvalue(), out.getvalue())


def test_watch_should_notice_a_writer_that_died_without_ending(directory: Path) -> None:
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    stream = events.Events(directory / "dead.jsonl")
    stream.emit("start", "council", pid=dead.pid)
    out = io.StringIO()
    result: list[int] = []
    watcher = threading.Thread(target=lambda: result.append(events.follow(stream.path, out, poll=0.05)), daemon=True)
    watcher.start()
    watcher.join(5)
    check("dead writer ends watch", result == [1] and "exited without finishing" in out.getvalue(), (result, out.getvalue()))


def test_codex_events_should_become_log_activity() -> None:
    command = json.dumps({"type": "item.started", "item": {"type": "command_execution", "command": "cat a.txt"}})
    message = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "I will read\n a.txt."}})
    check("codex command", providers.parse_codex_event(command)[1] == "tool: cat a.txt", providers.parse_codex_event(command))
    check("codex message", providers.parse_codex_event(message)[1] == "say: I will read a.txt.", providers.parse_codex_event(message))


def test_a_crashing_council_should_end_failed_not_look_alive(directory: Path) -> None:
    run_directory = directory / "run"
    run_directory.mkdir()
    state = {"id": "r1", "council": "coding", "feature": "f", "repository": "ai", "stage": "proposing", "plan": ["propose"]}
    (run_directory / "state.json").write_text(json.dumps(state), encoding="utf-8")
    run = council.Run(directory, run_directory)
    try:
        with council.Ticker(run):
            raise council.providers.ProviderError("codex not logged in")
    except council.providers.ProviderError:
        pass
    saved = json.loads((run_directory / "state.json").read_text(encoding="utf-8"))
    last = events.read(run.events.path)[-1]
    check("crash marks run failed", saved["stage"] == "failed" and "not logged in" in saved["summary"], saved)
    check("crash ends the stream", last["kind"] == events.END and not last["ok"], last)
    check("stream starts with owner pid", kinds(run.events.path)[0] == "start", kinds(run.events.path))


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        test_watchdog_should_report_a_silent_agent_once_per_period(directory)
        test_watch_should_exit_with_the_run_result(directory)
        test_watch_should_notice_a_writer_that_died_without_ending(directory)
        test_codex_events_should_become_log_activity()
        test_a_crashing_council_should_end_failed_not_look_alive(directory)
    for failure in FAILURES:
        print(f"FAIL {failure}")
    print("events tests: " + ("ok" if not FAILURES else f"{len(FAILURES)} failed"))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())

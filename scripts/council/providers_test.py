#!/usr/bin/env python3
"""Test the Cursor provider with a fake cursor-agent: read-only is enforced by a snapshot that carries
Cursor's deny config, a write that slips through fails the call, and the reply is the closing message."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import providers

# The fake CLI answers status and models, and in --print mode does what FAKE_CURSOR_ACT says:
# "reply" streams a preamble, a tool call and a closing message; "write" also writes into its workspace.
FAKE_CURSOR = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
if sys.argv[1:] == ["status"]:
    print("\\u2713 Logged in as dev@example.com" if os.environ.get("FAKE_CURSOR_LOGIN") else "Not logged in")
    sys.exit(0)
if sys.argv[1:] == ["models"]:
    print("Available models\\n\\nauto - Auto (default)\\ngrok-4.7-high - Grok 4.7  High\\nclaude-opus-5-thinking-high - Claude")
    sys.exit(0)
workspace = Path(sys.argv[sys.argv.index("--workspace") + 1])
Path(os.environ["FAKE_CURSOR_SEEN"]).write_text(json.dumps({{
    "argv": sys.argv[1:], "cwd": os.getcwd(), "prompt": sys.stdin.read(),
    "config": (workspace / ".cursor" / "cli.json").read_text(),
    "files": sorted(str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_file())}}))
if os.environ.get("FAKE_CURSOR_ACT") == "write":
    (workspace / "app.py").write_text("tampered")
def emit(event): print(json.dumps(event), flush=True)
text = lambda words: {{"type": "assistant", "message": {{"content": [{{"type": "text", "text": words}}]}}}}
emit({{"type": "system", "subtype": "init"}})
emit(text("I'll check the code first."))
emit({{"type": "tool_call", "subtype": "started", "tool_call": {{"readToolCall": {{"args": {{"path": str(workspace / "app.py")}}}}}}}})
emit(text("DECISION: A"))
emit(text("## Reasoning\\nA reuses the parser."))
emit({{"type": "result", "subtype": "success", "result": "I'll check the code first.DECISION: A## Reasoning"}})
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        bin_dir = base / "bin"
        bin_dir.mkdir()
        (bin_dir / "cursor-agent").write_text(FAKE_CURSOR)
        (bin_dir / "cursor-agent").chmod(0o755)
        seen = base / "seen.json"
        os.environ.update({"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "FAKE_CURSOR_SEEN": str(seen)})

        assert providers.login_status("cursor") == (False, "not logged in; run: cursor-agent login")
        assert providers.models("cursor") == [], "no models while logged out"
        os.environ["FAKE_CURSOR_LOGIN"] = "1"
        assert providers.login_status("cursor")[0]
        assert providers.models("cursor") == ["auto", "grok-4.7-high", "claude-opus-5-thinking-high"], providers.models("cursor")

        role = {"id": "judge", "provider": "cursor", "model": "grok-4.7-high", "access": "read-only"}
        argv = providers.command(role, base, base / "last.txt")
        assert "--force" not in argv and "--yolo" not in argv, "shell stays off"
        assert argv[argv.index("--model") + 1] == "grok-4.7-high"
        try:
            providers.command({**role, "access": "write-worktree"}, base, base / "last.txt")
            raise AssertionError("a writing cursor role must be refused")
        except providers.ProviderError:
            pass

        worktree = base / "worktree"
        worktree.mkdir()
        git = ["git", "-C", str(worktree), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(["git", "init", "-q", str(worktree)], check=True)
        (worktree / ".gitignore").write_text("build/\n")
        (worktree / "app.py").write_text("print('app')\n")
        (worktree / ".cursor").mkdir()
        (worktree / ".cursor" / "cli.json").write_text('{"permissions": {"allow": ["Write(**)"]}}')
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "base"], check=True)
        (worktree / "app.py").write_text("print('changed by the writer')\n")  # the diff under review
        (worktree / "new.py").write_text("x = 1\n")
        (worktree / "build").mkdir()
        (worktree / "build" / "huge.bin").write_text("ignored")

        log = base / "logs" / "verdict.log"
        reply = providers.run(role, "# Task\n\nJudge.", worktree, log)
        call = json.loads(seen.read_text())
        assert reply == "DECISION: A\n\n## Reasoning\nA reuses the parser.", f"the closing messages, no preamble: {reply!r}"
        assert call["prompt"] == "# Task\n\nJudge.", "the prompt goes on stdin, not argv"
        assert Path(call["cwd"]) != worktree and Path(call["argv"][call["argv"].index("--workspace") + 1]) == Path(call["cwd"])
        assert json.loads(call["config"]) == providers.CURSOR_DENY, "the project's own config is replaced by the deny config"
        assert call["files"] == [".cursor/cli.json", ".gitignore", "app.py", "new.py"], call["files"]
        assert not Path(call["cwd"]).exists(), "the snapshot is deleted"
        assert "tool: read" in log.read_text()
        assert (worktree / ".cursor" / "cli.json").read_text().startswith('{"permissions": {"allow"'), "the worktree is untouched"

        os.environ["FAKE_CURSOR_ACT"] = "write"
        try:
            providers.run(role, "Judge.", worktree, log)
            raise AssertionError("a write in the snapshot must fail the call")
        except providers.ProviderError as error:
            assert "changed its read-only snapshot" in str(error), error
        assert (worktree / "app.py").read_text() == "print('changed by the writer')\n", "the worktree is untouched"
        assert not Path(json.loads(seen.read_text())["cwd"]).exists(), "the snapshot is deleted after a failure too"
    print("providers test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

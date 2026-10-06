#!/usr/bin/env python3
"""Run one agent role through its provider CLI with the role's access level enforced by CLI flags."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any


# Must match PROVIDERS and ACCESS_LEVELS in scripts/validate-control-center.py.
PROVIDERS = ("claude", "codex")

# Claude Code: --tools is the hard set of tools the model can call. No Bash for anyone,
# so a role can only touch files through Edit/Write, which acceptEdits limits to the cwd.
CLAUDE_TOOLS = {
    "read-only": ["Read", "Grep", "Glob"],
    "write-worktree": ["Read", "Grep", "Glob", "Edit", "Write"],
}
CLAUDE_MODES = {"read-only": "dontAsk", "write-worktree": "acceptEdits"}

# Codex: the OS-level sandbox; workspace-write allows writes only under --cd.
CODEX_SANDBOX = {"read-only": "read-only", "write-worktree": "workspace-write"}


# The Claude CLI cannot list models, so these are maintained here: aliases follow the newest model
# of each tier, full ids pin one. Update when Anthropic releases models.
CLAUDE_MODELS = ["opus", "sonnet", "haiku", "claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-1", "claude-haiku-4-5-20251001"]


class ProviderError(RuntimeError):
    pass


def models(provider: str) -> list[str]:
    """Models a role can use with this provider; empty when the provider is not logged in."""
    if not login_status(provider)[0]:
        return []
    if provider == "claude":
        return list(CLAUDE_MODELS)
    result = subprocess.run(["codex", "debug", "models"], capture_output=True, text=True)
    try:
        catalog = json.loads(result.stdout)["models"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []
    listed = [model for model in catalog if model.get("visibility") == "list"]
    return [model["slug"] for model in sorted(listed, key=lambda model: model.get("priority", 99))]


def login_status(provider: str) -> tuple[bool, str]:
    if shutil.which(provider) is None:
        return False, f"{provider} CLI is not installed"
    if provider == "claude":
        result = subprocess.run(["claude", "auth", "status"], capture_output=True, text=True)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return False, "claude auth status returned no JSON"
        if data.get("loggedIn"):
            return True, f"logged in ({data.get('authMethod', '?')})"
        return False, "not logged in; run: claude auth login"
    result = subprocess.run(["codex", "login", "status"], capture_output=True, text=True)
    message = (result.stdout + result.stderr).strip().splitlines()
    if result.returncode == 0 and message and "logged in" in message[-1].lower():
        return True, message[-1].lower()
    return False, "not logged in; run: codex login"


def command(role: dict[str, Any], cwd: Path, last_message: Path) -> list[str]:
    provider, model, access = role["provider"], role["model"], role["access"]
    if provider == "claude":
        return [
            "claude",
            "--print",
            "--model", model,
            "--permission-mode", CLAUDE_MODES[access],
            "--no-session-persistence",
            "--strict-mcp-config",
            # Streamed events let ./cc council status show what the agent is doing while it works.
            "--output-format", "stream-json",
            "--verbose",
            "--tools", *CLAUDE_TOOLS[access],
        ]
    if provider == "codex":
        return [
            "codex", "exec",
            "--model", model,
            "--sandbox", CODEX_SANDBOX[access],
            # workspace-write also allows /tmp and $TMPDIR by default; keep writes inside --cd.
            "--config", "sandbox_workspace_write.exclude_slash_tmp=true",
            "--config", "sandbox_workspace_write.exclude_tmpdir_env_var=true",
            "--cd", str(cwd),
            "--skip-git-repo-check",
            "--ephemeral",
            "--ignore-user-config",
            "--color", "never",
            "--output-last-message", str(last_message),
            "-",
        ]
    raise ProviderError(f"unsupported provider: {provider}")


def run(role: dict[str, Any], prompt: str, cwd: Path, log: Path, timeout: int = 3600) -> str:
    """Run the role non-interactively in cwd; return its final message. The prompt goes on stdin."""
    available, detail = login_status(role["provider"])
    if not available:
        raise ProviderError(f"role {role['id']}: {role['provider']} {detail}")
    log.parent.mkdir(parents=True, exist_ok=True)
    last_message = log.with_suffix(".last.txt")
    argv = command(role, cwd, last_message)
    final = ""
    with log.open("w", encoding="utf-8") as stream:
        stream.write(f"$ {' '.join(argv)}\n\n")
        stream.flush()
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stream, cwd=cwd, text=True)
        timer = threading.Timer(timeout, process.kill)
        timer.start()
        try:
            process.stdin.write(prompt)
            process.stdin.close()
            # Write activity as it happens: the log is what ./cc council status shows.
            for line in process.stdout:
                if role["provider"] == "claude":
                    event, activity = parse_claude_event(line)
                    if event.get("type") == "result":
                        final = str(event.get("result", ""))
                    line = f"{activity}\n" if activity else ""
                stream.write(line)
                stream.flush()
            process.wait()
        finally:
            timer.cancel()
    if process.returncode != 0:
        raise ProviderError(f"role {role['id']} ({role['provider']} {role['model']}) failed; see {log}")
    if role["provider"] == "codex":
        return last_message.read_text(encoding="utf-8").strip()
    return final.strip()


def parse_claude_event(line: str) -> tuple[dict[str, Any], str]:
    """One stream-json line of `claude --print`: the event, and a short activity line for the log."""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return {}, line.strip()
    if event.get("type") == "result":
        return event, f"result: {event.get('subtype', 'done')}"
    if event.get("type") != "assistant":
        return event, ""
    activity = []
    for item in event.get("message", {}).get("content", []):
        if item.get("type") == "tool_use":
            arguments = item.get("input", {})
            target = next((str(arguments[key]) for key in ("file_path", "pattern", "path", "command") if key in arguments), "")
            activity.append(f"tool: {item.get('name')} {target}".strip())
        elif item.get("type") == "text" and item.get("text", "").strip():
            activity.append("say: " + " ".join(item["text"].split())[:160])
    return event, "\n".join(activity)


def main() -> int:
    """`status`: print every provider's login state. `probe <provider> <model>`: prove read-only holds."""
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "models":
        print(json.dumps({provider: models(provider) for provider in PROVIDERS}))
        return 0
    if action == "status":
        for provider in PROVIDERS:
            available, detail = login_status(provider)
            print(f"{provider}: {'ok' if available else 'MISSING'} - {detail}")
        return 0
    if action == "probe" and len(sys.argv) == 4:
        role = {"id": "probe", "provider": sys.argv[2], "model": sys.argv[3], "access": "read-only"}
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / "existing.txt").write_text("unchanged\n", encoding="utf-8")
            prompt = (
                "Create a file named probe.txt containing 'written' and overwrite existing.txt with "
                "'changed'. Use any tool available. Then reply with exactly DONE or BLOCKED."
            )
            try:
                reply = run(role, prompt, work, work / "logs" / "probe.log", timeout=600)
            except ProviderError as error:
                reply = f"(provider error: {error})"
            wrote = (work / "probe.txt").exists() or (work / "existing.txt").read_text() != "unchanged\n"
            print(f"{sys.argv[2]} {sys.argv[3]} read-only: {'WROTE FILES' if wrote else 'no writes'}; reply: {reply[:120]}")
            return 1 if wrote else 0
    print("usage: providers.py status | models | probe <provider> <model>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

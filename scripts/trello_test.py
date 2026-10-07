#!/usr/bin/env python3
"""Test ./cc trello against a local fake Trello API: nothing is sent without --yes, the token never leaks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "trello.py"
TOKEN = "secret-token-123"
LISTS = [{"id": "L1", "name": "To do"}, {"id": "L2", "name": "In progress"}, {"id": "L3", "name": "Done"}]
SENT: list[tuple[str, str, dict]] = []


class FakeTrello(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass

    def answer(self, status: int, body: object) -> None:
        self.send_response(status)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def route(self, method: str) -> None:
        url = urllib.parse.urlparse(self.path)
        query = dict(urllib.parse.parse_qsl(url.query))
        if query.get("token") != TOKEN:
            return self.answer(401, "invalid token")
        path = url.path.removeprefix("/1")
        if method in {"POST", "PUT"}:
            SENT.append((method, path, query))
        if path == "/members/me/boards":
            return self.answer(200, [{"name": "PV board", "shortLink": "Bd1"}])
        if path == "/boards/Bd1":
            return self.answer(200, {"name": "PV board", "shortLink": "Bd1"})
        if path == "/boards/Bd1/lists":
            return self.answer(200, LISTS)
        if path == "/cards/Cd1" and method == "GET":
            return self.answer(200, {"name": "Agent health API", "shortUrl": "https://trello.com/c/Cd1", "idList": "L2",
                                     "desc": "Agents report health every 30 s."})
        if path == "/cards/Cd1/checklists":
            return self.answer(200, [{"name": "Acceptance", "checkItems": [
                {"name": "Returns 200 with status per device", "state": "complete"}, {"name": "Rejects unknown agents", "state": "incomplete"}]}])
        if path == "/lists/L2":
            return self.answer(200, {"name": "In progress"})
        if path in {"/cards/Cd1/actions/comments", "/cards/Cd1"}:
            return self.answer(200, {})
        return self.answer(404, "not found")

    def do_GET(self) -> None:
        self.route("GET")

    def do_POST(self) -> None:
        self.route("POST")

    def do_PUT(self) -> None:
        self.route("PUT")


def main() -> int:
    server = HTTPServer(("127.0.0.1", 0), FakeTrello)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        root = base / "x_CC"
        (root / "plans/active").mkdir(parents=True)
        (root / "control-center.json").write_text(json.dumps({"layout": {"worktrees": "../worktrees"}}))
        (root / "plans/active/health.md").write_text("# health: Health\n\nLifecycle: active\nPlanning status: accepted\n\n## Outcome\n")
        (base / "worktrees/feat").mkdir(parents=True)
        (base / "worktrees/feat/.cc-worktree.json").write_text(json.dumps({"feature": "feat", "repositories": {}}))
        credentials = base / "trello.env"
        environment = {**os.environ, "TRELLO_API_BASE": f"http://127.0.0.1:{server.server_port}/1", "CC_TRELLO_ENV": str(credentials)}
        environment.pop("TRELLO_API_KEY", None)
        environment.pop("TRELLO_TOKEN", None)

        def cc(*arguments: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run([sys.executable, str(SCRIPT), str(root), *arguments], env=environment, capture_output=True, text=True)

        out = cc("status").stdout
        assert "credentials: MISSING" in out, out
        credentials.write_text(f"TRELLO_API_KEY=key-1\nTRELLO_TOKEN={TOKEN}\n")

        bad = cc("connect", "--board", "https://trello.com/b/Bd1/pv", "--active-list", "Doing")
        assert bad.returncode == 1 and "Doing" in bad.stderr and "In progress" in bad.stderr, bad.stderr
        assert cc("connect", "--board", "https://trello.com/b/Bd1/pv").returncode == 0
        saved = json.loads((root / "catalog/integrations/trello.json").read_text())
        assert saved["lists"] == {"active": "In progress", "completed": "Done"} and saved["board"] == "Bd1", saved
        assert "active     -> In progress" in cc("status").stdout

        assert cc("link", "--plan", "health", "https://trello.com/c/Cd1/7-agent-health").returncode == 0
        plan = (root / "plans/active/health.md").read_text()
        assert "Planning status: accepted\nTrello: https://trello.com/c/Cd1/7-agent-health\n" in plan, plan
        assert cc("link", "--feature", "feat", "https://trello.com/c/Cd1/7").returncode == 0
        assert "In progress" in cc("show", "--feature", "feat").stdout
        # A card linked from a PR: its description and checklists are the review's acceptance criteria.
        card = cc("show", "--card", "https://trello.com/c/Cd1/7-agent-health").stdout
        assert "every 30 s" in card and "[x] Returns 200" in card and "[ ] Rejects unknown agents" in card, card

        preview = cc("comment", "--plan", "health", "--text", "Verify passed on windows.")
        assert "PREVIEW, nothing sent" in preview.stdout and not SENT, (preview.stdout, SENT)
        assert "PREVIEW, nothing sent" in cc("move", "--plan", "health", "completed").stdout and not SENT
        assert cc("comment", "--plan", "health", "--text", "Verify passed on windows.", "--yes").returncode == 0
        assert cc("move", "--feature", "feat", "completed", "--yes").returncode == 0
        assert SENT[0][:2] == ("POST", "/cards/Cd1/actions/comments") and SENT[0][2]["text"] == "Verify passed on windows.", SENT
        assert SENT[1][:2] == ("PUT", "/cards/Cd1") and SENT[1][2]["idList"] == "L3", SENT

        assert cc("link", "--plan", "health", "https://trello.com/c/Zz9/x").returncode == 0
        failure = cc("show", "--plan", "health")
        assert failure.returncode == 1 and "HTTP 404" in failure.stderr and TOKEN not in failure.stderr + failure.stdout, failure.stderr
    server.shutdown()
    print("trello test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

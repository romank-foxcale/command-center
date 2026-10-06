#!/usr/bin/env python3
"""./cc ui: a terminal dashboard for one Control Center. Reads files; changes go through ./cc."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from rich.markup import escape
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Input, Label, OptionList, Static, TabbedContent, TabPane
from textual.widgets.option_list import Option

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state import Snapshot, snapshot  # noqa: E402
from progress import SPINNER  # noqa: E402  (state.py puts scripts/council on the path)

TABS = ("runs", "plans", "agents", "councils", "repos", "worktrees")


def available_models(root: Path) -> dict[str, list[str]]:
    """Models per logged-in provider, from the CC's own provider adapter."""
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "council" / "providers.py"), "models"], capture_output=True, text=True
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        # An older CC whose provider adapter cannot list models yet, or a broken one: say so.
        raise RuntimeError((result.stderr or result.stdout).strip()[-300:] or "providers.py models printed nothing") from None

FACES = {
    "calm": ("◉   ◉", " ─── "),
    "working": ("◔   ◔", " ─── "),
    "alert": ("◉   ◉", " ─o─ "),
    "grim": ("×   ×", " ─── "),
}
LINES = {
    "calm": [
        "{verified} repos green. Did you check, or did you hope?",
        "Nothing is broken. Yet.",
        "A clean worktree is a quiet conscience.",
        "No council is waiting. Neither should you.",
    ],
    "working": [
        "{active} council run(s) at work. Watching.",
        "Somewhere a model is thinking. Let it.",
        "The writer writes. The tests will judge.",
    ],
    "alert": [
        "A council awaits your word. It will not decide for you.",
        "{waiting} verdict(s) on your desk. Read them.",
        "The judge has spoken. Now you.",
    ],
    "grim": [
        "Something stopped: {problem}.",
        "Red is information. Ignore it at your price.",
        "A stalled run does not finish itself.",
    ],
}


def mood(state: Snapshot) -> str:
    if state.problems:
        return "grim"
    if state.waiting:
        return "alert"
    if state.active_runs:
        return "working"
    return "calm"


def mascot(face: str) -> str:
    eyes, mouth = FACES[face]
    return "\n".join(
        [
            "   ▗▄▄▄▄▄▄▄▖",
            "  ▐██▀▀▀▀▀██▌",
            f"  ▐█  {eyes} █▌",
            f"  ▐█  {mouth} █▌",
            "   ▝▀█▄▄▄▄█▀▘",
            "     ▝▘   ▝▘",
        ]
    )


class Ask(ModalScreen[list[str] | None]):
    """A small form: one input per field, or just a confirmation when there are none."""

    def __init__(self, title: str, fields: list[tuple[str, str]]):
        super().__init__()
        self.title_text = title
        self.fields = fields

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.title_text)
            for placeholder, value in self.fields:
                yield Input(value=value, placeholder=placeholder)
            with Horizontal():
                yield Button("OK", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss([field.value.strip() for field in self.query(Input)] if event.button.id == "ok" else None)

    def on_input_submitted(self) -> None:
        self.dismiss([field.value.strip() for field in self.query(Input)])


class ModelPicker(ModalScreen[tuple[str, str] | None]):
    """Every model of every logged-in provider, grouped under a provider header."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, role: str, current: tuple[str, str], models: dict[str, list[str]]):
        super().__init__()
        self.role = role
        self.current = current
        self.models = models

    def compose(self) -> ComposeResult:
        options: list[Option] = []
        highlight = None
        for provider, names in self.models.items():
            if not names:
                continue
            options.append(Option(Text(provider, style="bold reverse"), disabled=True))
            for name in names:
                if (provider, name) == self.current:
                    highlight = len(options)
                options.append(Option(f"  {name}", id=f"{provider}	{name}"))
        with Vertical(id="dialog"):
            yield Label(f"[b]{self.role}[/b] uses {self.current[0]} {self.current[1]} · Enter choose · Esc cancel")
            if options:
                picker = OptionList(*options, id="models")
                picker.highlighted = highlight
                yield picker
            else:
                yield Label("No provider is logged in: run claude auth login or codex login.")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        provider, name = event.option.id.split("	", 1)
        self.dismiss((provider, name))

    def action_cancel(self) -> None:
        self.dismiss(None)


class Dashboard(App):
    TITLE = "Control Center"
    CSS = """
    #top { height: 8; }
    #mascot { width: 18; color: $text; }
    #summary { padding: 1 2; }
    #dialog { width: 70; height: auto; border: heavy $accent; padding: 1 2; background: $surface; }
    Ask, ModelPicker { align: center middle; }
    #models { height: auto; max-height: 20; }
    DataTable { height: 1fr; }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "approve", "Approve run"),
        Binding("p", "pick", "Pick proposal"),
        Binding("x", "reject", "Reject run"),
        Binding("e", "edit", "Edit selected"),
        Binding("left", "tab(-1)", "Prev tab", priority=True),
        Binding("right", "tab(1)", "Next tab", priority=True),
    ]

    def __init__(self, root: Path, models=available_models):
        super().__init__()
        self.root = root
        self.models = models
        self.state = snapshot(root)
        self.line = 0

    def compose(self) -> ComposeResult:
        with Horizontal(id="top"):
            yield Static(id="mascot")
            yield Static(id="summary")
        with TabbedContent(id="tabs"):
            for tab, columns in (
                ("Runs", ("run", "council", "feature/repo", "status", "progress", "current step · agents", "time", "summary")),
                ("Plans", ("plan", "lifecycle", "planning", "title")),
                ("Agents", ("role", "provider", "model", "access")),
                ("Councils", ("council", "kind", "proposers", "judge", "writer", "approval", "retries")),
                ("Repos", ("repo", "status", "targets", "stack", "role")),
                ("Worktrees", ("feature", "repo", "branch", "changes")),
            ):
                with TabPane(tab, id=tab.lower()):
                    table = DataTable(id=f"t-{tab.lower()}", cursor_type="row", zebra_stripes=True)
                    table.add_columns(*columns)
                    yield table
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = str(self.root)
        self.render_state()
        # Every second, so run timers and the spinner move.
        self.set_interval(1, self.action_refresh)

    def action_tab(self, step: int) -> None:
        if isinstance(self.screen, ModalScreen):
            return
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = TABS[(TABS.index(tabs.active) + step) % len(TABS)]

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        # Keep the arrow keys on the rows of whichever tab is showing.
        self.query_one(f"#t-{event.pane.id}", DataTable).focus()

    # Rendering -----------------------------------------------------------------------

    def action_refresh(self) -> None:
        self.state = snapshot(self.root)
        self.line = int(time.time() // 20)
        self.render_state()

    def render_state(self) -> None:
        state = self.state
        face = mood(state)
        options = LINES[face]
        text = options[self.line % len(options)].format(
            verified=sum(repo["status"] == "verified" for repo in state.repos),
            active=len(state.active_runs),
            waiting=len(state.waiting),
            problem=(state.problems or ["?"])[0],
        )
        self.query_one("#mascot", Static).update(mascot(face))
        active_plans = [plan for plan in state.plans if plan["lifecycle"] == "active"]
        tools = "  ".join(f"{tool} {'✓' if ok else '✗'}" for tool, ok in state.tools.items())
        verified = sum(repo["status"] == "verified" for repo in state.repos)
        spinner = f"{SPINNER[int(time.time()) % len(SPINNER)]} " if state.active_runs else ""
        summary = (
            f"[b]{escape(state.name)}[/b] · {escape(state.status)}        {tools}\n"
            f"{len(active_plans)} plan(s) active · {spinner}{len(state.active_runs)} run(s) working · "
            f"[b]{len(state.waiting)} waiting for you[/b] · {verified}/{len(state.repos)} repos verified\n\n"
            f"[i]\"{escape(text)}\"[/i]"
        )
        if state.problems:
            summary += "\n[b red]" + escape(" · ".join(state.problems[:3])) + "[/b red]"
        self.query_one("#summary", Static).update(summary)

        self.fill("runs", [(r["id"], r["council"], r["target"], self.paint(r["status"]), r["progress"], r["step"], r["time"], r["summary"][:60]) for r in state.runs])
        self.fill("plans", [(p["id"], p["lifecycle"], p["planning"], p["title"]) for p in state.plans])
        self.fill("agents", [(r["id"], r["provider"], r["model"], r["access"]) for r in state.roles])
        self.fill(
            "councils",
            [(c["id"], c["kind"], c["proposers"], c["judge"], c["writer"], "on" if c["approval"] else "off", str(c["maxRetries"])) for c in state.councils],
        )
        self.fill("repos", [(r["id"], self.paint(r["status"]), r["targets"], r["stack"], r["role"]) for r in state.repos])
        self.fill("worktrees", [(w["feature"], w["repo"], w["branch"], w["changes"]) for w in state.worktrees])

    @staticmethod
    def paint(status: str) -> Text:
        if status == "awaiting-approval":
            return Text(status, style="bold yellow")
        if status.startswith("stalled") or status in {"failed", "verify-failed", "blocked-security", "blocked"}:
            return Text(status, style="bold red")
        if status in {"done", "verified"}:
            return Text(status, style="green")
        return Text(status)

    def fill(self, tab: str, rows: list[tuple]) -> None:
        table = self.query_one(f"#t-{tab}", DataTable)
        cursor = table.cursor_row
        table.clear()
        for row in rows:
            table.add_row(*(cell if isinstance(cell, Text) else Text(str(cell)) for cell in row), key=str(row[0]))
        if rows:
            table.move_cursor(row=min(cursor, len(rows) - 1))

    def selected(self, tab: str) -> str | None:
        table = self.query_one(f"#t-{tab}", DataTable)
        if not table.row_count:
            return None
        return str(table.get_row_at(table.cursor_row)[0].plain)

    # Actions: every change goes through ./cc ------------------------------------------

    def cc(self, *arguments: str, background: str | None = None) -> None:
        command = [str(self.root / "cc"), *arguments]
        if background:
            # Long council steps outlive the dashboard; their output goes to the run folder.
            log = open(background, "a", encoding="utf-8")
            subprocess.Popen(command, cwd=self.root, stdout=log, stderr=log, start_new_session=True)
            self.notify(f"started: ./cc {' '.join(arguments)}")
            return
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        output = (result.stdout + result.stderr).strip() or "done"
        self.notify(output[-400:], severity="information" if result.returncode == 0 else "error", timeout=8)
        self.action_refresh()

    def waiting_run(self) -> dict | None:
        self.query_one("#tabs", TabbedContent).active = "runs"
        identifier = self.selected("runs")
        run = next((run for run in self.state.runs if run["id"] == identifier), None)
        if not run or run["status"] != "awaiting-approval":
            self.notify("select a run that is awaiting approval", severity="warning")
            return None
        return run

    def action_approve(self) -> None:
        run = self.waiting_run()
        if run:
            authors = ", ".join(f"{label}: {role}" for label, role in run["labels"].items())
            note = Ask(f"Approve {run['id']}? Authors: {authors}. Optional note for the writer:", [("note (optional)", "")])
            self.push_screen(note, lambda answer: answer is not None and self.cc(
                "council", "approve", run["id"], *(["--note", answer[0]] if answer[0] else []),
                background=f"{run['directory']}/approve.log"))

    def action_pick(self) -> None:
        run = self.waiting_run()
        if run:
            labels = "/".join(run["labels"])
            self.push_screen(Ask(f"Use which proposal instead of the verdict ({labels})?", [("label", "")]),
                lambda answer: answer and answer[0] and self.cc(
                    "council", "approve", run["id"], "--pick", answer[0], background=f"{run['directory']}/approve.log"))

    def action_reject(self) -> None:
        run = self.waiting_run()
        if run:
            self.push_screen(Ask(f"Reject {run['id']}?", []), lambda answer: answer is not None and self.cc("council", "reject", run["id"]))

    def pick_model(self, role: str, current: tuple[str, str]) -> None:
        """Runs in a worker thread: listing Codex models takes a moment."""
        try:
            models = self.models(self.root)
        except RuntimeError as error:
            self.call_from_thread(self.notify, f"cannot list models: {error}", severity="error", timeout=10)
            return
        self.call_from_thread(
            self.push_screen,
            ModelPicker(role, current, models),
            lambda choice: choice and self.cc("council", "set-role", role, "--provider", choice[0], "--model", choice[1]),
        )

    def action_edit(self) -> None:
        tab = self.query_one("#tabs", TabbedContent).active
        item = self.selected(tab)
        if not item:
            return
        if tab == "agents":
            role = next(role for role in self.state.roles if role["id"] == item)
            self.notify("loading models of the logged-in providers...", timeout=2)
            self.run_worker(lambda: self.pick_model(item, (role["provider"], role["model"])), thread=True)
        elif tab == "councils":
            council = next(council for council in self.state.councils if council["id"] == item)
            self.push_screen(Ask(f"Council {item}: approval pause (on/off) and max retries (0-5)",
                [("on or off", "on" if council["approval"] else "off"), ("max retries", str(council["maxRetries"]))]),
                lambda answer: answer and self.cc("council", "set", item, "--approval", answer[0], "--max-retries", answer[1]))
        elif tab == "repos":
            repo = next(repo for repo in self.state.repos if repo["id"] == item)
            def apply(answer: list[str] | None) -> None:
                if not answer:
                    return
                if answer[0] != repo["targets"]:
                    self.cc("repo", "set-targets", item, *answer[0].replace(",", " ").split())
                if answer[1] != repo["stack"]:
                    self.cc("repo", "set-stack", item, *answer[1].replace(",", " ").split())
            self.push_screen(Ask(f"Repo {item}: target platforms and stack (comma-separated)",
                [("windows, linux, macos", repo["targets"]), ("languages", repo["stack"])]), apply)
        else:
            self.notify("e edits roles (Agents), councils (Councils) and repos (Repos)", severity="warning")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    Dashboard(root).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

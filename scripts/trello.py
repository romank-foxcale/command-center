#!/usr/bin/env python3
"""Trello for a Control Center, on demand only: connect a board, link cards to plans and features,
post comments and move cards. Nothing is sent without --yes; credentials never enter a repository."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API = os.environ.get("TRELLO_API_BASE", "https://api.trello.com/1")
CREDENTIALS = Path(os.environ.get("CC_TRELLO_ENV", Path.home() / ".config" / "cc" / "trello.env"))
CARD_URL = re.compile(r"https://trello\.com/c/([A-Za-z0-9]+)")
PLAN_FIELD = re.compile(r"^Trello:\s*(\S+)\s*$", re.MULTILINE)
# Plan lifecycle -> the board list a card moves to; the user maps these to their list names.
LIST_KEYS = ("active", "completed")


class TrelloError(RuntimeError):
    pass


def credentials() -> tuple[str, str]:
    values = {key: os.environ.get(key, "") for key in ("TRELLO_API_KEY", "TRELLO_TOKEN")}
    if CREDENTIALS.is_file():
        for line in CREDENTIALS.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() in values and not values[key.strip()]:
                values[key.strip()] = value.strip().strip('"')
    if not all(values.values()):
        raise TrelloError(f"no Trello credentials: put TRELLO_API_KEY and TRELLO_TOKEN in {CREDENTIALS}")
    return values["TRELLO_API_KEY"], values["TRELLO_TOKEN"]


def call(method: str, path: str, **params: str) -> Any:
    key, token = credentials()
    query = urllib.parse.urlencode({**params, "key": key, "token": token})
    request = urllib.request.Request(f"{API}{path}?{query}", method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        # Never echo the URL: it carries the token.
        raise TrelloError(f"Trello {method} {path}: HTTP {error.code} {error.read().decode(errors='replace')[:200]}") from None
    except urllib.error.URLError as error:
        raise TrelloError(f"Trello unreachable: {error.reason}") from None


def config_path(root: Path) -> Path:
    return root / "catalog" / "integrations" / "trello.json"


def config(root: Path) -> dict[str, Any]:
    path = config_path(root)
    if not path.is_file():
        raise TrelloError("no board connected: run ./cc trello connect --board <board url or id>")
    return json.loads(path.read_text(encoding="utf-8"))


def board_lists(board: str) -> dict[str, str]:
    return {item["name"]: item["id"] for item in call("GET", f"/boards/{board}/lists", filter="open")}


# Links ---------------------------------------------------------------------------------


def plan_file(root: Path, identifier: str) -> Path:
    for lifecycle in ("active", "archived", "completed"):
        path = root / "plans" / lifecycle / f"{identifier}.md"
        if path.is_file():
            return path
    raise TrelloError(f"plan does not exist: {identifier}")


def feature_manifest(root: Path, feature: str) -> Path:
    layout = json.loads((root / "control-center.json").read_text(encoding="utf-8"))["layout"]
    path = (root / layout["worktrees"]).resolve() / feature / ".cc-worktree.json"
    if not path.is_file():
        raise TrelloError(f"feature does not exist: {feature}")
    return path


def linked_card(root: Path, args: argparse.Namespace) -> str:
    if getattr(args, "card", None):
        match = CARD_URL.match(args.card)
        if not match:
            raise TrelloError("give the card's URL, like https://trello.com/c/AbCd1234/...")
        return match.group(1)
    if args.plan:
        match = PLAN_FIELD.search(plan_file(root, args.plan).read_text(encoding="utf-8"))
        url = match.group(1) if match else ""
    else:
        url = json.loads(feature_manifest(root, args.feature).read_text(encoding="utf-8")).get("trelloCard", "")
    match = CARD_URL.match(url)
    if not match:
        target = f"plan {args.plan}" if args.plan else f"feature {args.feature}"
        raise TrelloError(f"{target} has no Trello card: run ./cc trello link")
    return match.group(1)


def command_link(root: Path, args: argparse.Namespace) -> None:
    if not CARD_URL.match(args.card):
        raise TrelloError("give the card's URL, like https://trello.com/c/AbCd1234/...")
    if args.plan:
        path = plan_file(root, args.plan)
        text = path.read_text(encoding="utf-8")
        line = f"Trello: {args.card}"
        if PLAN_FIELD.search(text):
            text = PLAN_FIELD.sub(line, text, count=1)
        else:
            text = re.sub(r"^(Planning status:.*)$", rf"\1\n{line}", text, count=1, flags=re.MULTILINE)
        path.write_text(text, encoding="utf-8")
        print(f"plan {args.plan} linked to {args.card}")
    else:
        path = feature_manifest(root, args.feature)
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["trelloCard"] = args.card
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"feature {args.feature} linked to {args.card}")


# Commands ------------------------------------------------------------------------------


def command_status(root: Path, args: argparse.Namespace) -> None:
    try:
        credentials()
        print(f"credentials: found ({CREDENTIALS if CREDENTIALS.is_file() else 'environment'})")
    except TrelloError as error:
        print(f"credentials: MISSING - {error}")
        return
    if not config_path(root).is_file():
        print("board: not connected (./cc trello connect --board <board url or id>)")
        return
    settings = config(root)
    lists = board_lists(settings["board"])
    print(f"board: {settings.get('name', settings['board'])} ({settings['board']})")
    for key in LIST_KEYS:
        name = settings["lists"].get(key)
        print(f"  {key:<10} -> {name or '(not mapped)'}{'' if not name or name in lists else '  MISSING ON BOARD'}")


def command_boards(root: Path, args: argparse.Namespace) -> None:
    for board in call("GET", "/members/me/boards", filter="open", fields="name,shortLink"):
        print(f"{board['shortLink']}\t{board['name']}")


def command_lists(root: Path, args: argparse.Namespace) -> None:
    board = args.board or config(root)["board"]
    for name in board_lists(board):
        print(name)


def command_connect(root: Path, args: argparse.Namespace) -> None:
    board = re.sub(r"^https://trello\.com/b/([A-Za-z0-9]+).*$", r"\1", args.board)
    info = call("GET", f"/boards/{board}", fields="name,shortLink")
    lists = board_lists(board)
    mapping = {"active": args.active_list, "completed": args.completed_list}
    missing = [name for name in mapping.values() if name not in lists]
    if missing:
        raise TrelloError(f"lists not on board {info['name']}: {', '.join(missing)}; it has: {', '.join(lists)}")
    path = config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schemaVersion": 1, "board": info["shortLink"], "name": info["name"], "lists": mapping}, indent=2) + "\n", encoding="utf-8")
    print(f"connected board {info['name']}: active -> {args.active_list}, completed -> {args.completed_list}")


def command_show(root: Path, args: argparse.Namespace) -> None:
    identifier = linked_card(root, args)
    card = call("GET", f"/cards/{identifier}", fields="name,desc,shortUrl,idList")
    listing = call("GET", f"/lists/{card['idList']}", fields="name")
    print(f"{card['name']}\n  list: {listing['name']}\n  {card['shortUrl']}")
    # The description and checklists usually hold the scope and acceptance criteria a review checks against.
    if card.get("desc", "").strip():
        print(f"\ndescription:\n{card['desc'].strip()}")
    for checklist in call("GET", f"/cards/{identifier}/checklists", fields="name") or []:
        print(f"\nchecklist: {checklist.get('name', '')}")
        for item in checklist.get("checkItems", []):
            print(f"  [{'x' if item.get('state') == 'complete' else ' '}] {item.get('name', '')}")


def command_comment(root: Path, args: argparse.Namespace) -> None:
    text = Path(args.file).read_text(encoding="utf-8") if args.file else args.text
    if not text or not text.strip():
        raise TrelloError("give the comment with --text or --file")
    card = linked_card(root, args)
    if not args.yes:
        print(f"PREVIEW, nothing sent. Comment for card {card}:\n\n{text.strip()}\n\nSend it with --yes.")
        return
    call("POST", f"/cards/{card}/actions/comments", text=text.strip())
    print(f"comment posted to card {card}")


def command_move(root: Path, args: argparse.Namespace) -> None:
    settings = config(root)
    name = settings["lists"].get(args.to, args.to)
    lists = board_lists(settings["board"])
    if name not in lists:
        raise TrelloError(f"no list {name!r} on the board; lists: {', '.join(lists)}")
    card = linked_card(root, args)
    if not args.yes:
        print(f"PREVIEW, nothing sent. Move card {card} to list {name!r}. Send it with --yes.")
        return
    call("PUT", f"/cards/{card}", idList=lists[name])
    print(f"card {card} moved to {name}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="./cc trello")
    result.add_argument("root", type=Path)
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="credentials, board and list mapping").set_defaults(handler=command_status)
    sub.add_parser("boards", help="your open boards").set_defaults(handler=command_boards)
    lists = sub.add_parser("lists", help="lists of the connected board, or of --board")
    lists.add_argument("--board")
    lists.set_defaults(handler=command_lists)
    connect = sub.add_parser("connect", help="connect this CC to a board and map plan states to lists")
    connect.add_argument("--board", required=True, help="board URL or short id")
    connect.add_argument("--active-list", default="In progress")
    connect.add_argument("--completed-list", default="Done")
    connect.set_defaults(handler=command_connect)

    def target(command: argparse.ArgumentParser, card: bool = False) -> argparse.ArgumentParser:
        group = command.add_mutually_exclusive_group(required=True)
        group.add_argument("--plan")
        group.add_argument("--feature")
        if card:
            group.add_argument("--card", help="a card URL, e.g. one linked from a pull request")
        return command

    link = target(sub.add_parser("link", help="link a plan or feature to a card"))
    link.add_argument("card", help="card URL")
    link.set_defaults(handler=command_link)
    target(sub.add_parser("show", help="the linked card, its description and checklists"), card=True).set_defaults(handler=command_show)
    comment = target(sub.add_parser("comment", help="comment on the linked card (preview unless --yes)"))
    comment.add_argument("--text")
    comment.add_argument("--file")
    comment.add_argument("--yes", action="store_true", help="really send it")
    comment.set_defaults(handler=command_comment)
    move = target(sub.add_parser("move", help="move the linked card (preview unless --yes)"))
    move.add_argument("to", help="active, completed or a list name")
    move.add_argument("--yes", action="store_true", help="really send it")
    move.set_defaults(handler=command_move)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        args.handler(args.root.resolve(), args)
    except (TrelloError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

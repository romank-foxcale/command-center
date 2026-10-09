#!/usr/bin/env python3
"""./cc prs threads|judge: the review conversations of one catalog PR that wait on the user, judged by
fresh read-only sceptics that see only the claim, the code at the PR head and the CC's notes.

On the user's own PR, the claims are the other people's comments. On someone else's PR, they are the
replies to the user's comments. People are anonymized: the sceptics never learn who anyone is, or which
side the user is on. When the sceptics agree, their verdict stands; when they split, the threads
council's judge settles it from their anonymous replies. Nothing is ever posted from here.

Local state (.cc-local/threads/<repo>-<n>.json) keeps, per thread, only the id of the last comment
judged and the verdict: never comment bodies, prompts or replies."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import json
import os
import random
import re
import secrets
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "council"))
import events  # noqa: E402
import prs  # noqa: E402
import providers  # noqa: E402
from run import skill_text  # noqa: E402

PAGE = 100
QUERY = """query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number title url headRefOid author { login }
      reviewThreads(first: %(page)d) {
        pageInfo { hasNextPage }
        nodes {
          id isResolved isOutdated path line originalLine
          comments(first: %(page)d) { nodes { id author { login } body createdAt url originalCommit { oid } } }
        }
      }
      reviews(first: %(page)d) { pageInfo { hasNextPage } nodes { id author { login } body submittedAt url } }
      comments(first: %(page)d) { pageInfo { hasNextPage } nodes { id author { login } body createdAt url } }
    }
  }
}""" % {"page": PAGE}

VERDICTS = {
    "comment": ("VALID", "OUT-OF-SCOPE", "REFUTED", "NEEDS-INFO", "PREFERENCE"),
    "reply": ("ADDRESSED", "NOT-ADDRESSED", "PUSHBACK-HOLDS", "PUSHBACK-FAILS"),
}
# A verdict that rests on the code needs evidence; these two say the code cannot settle it.
UNEVIDENCED = {"PREFERENCE", "NEEDS-INFO"}
UNJUDGED = "UNJUDGED"
PARALLEL = 4
TIMEOUT = 1200


# GitHub data -------------------------------------------------------------------------------------------


def login() -> str:
    return prs.gh("api", "user", "--jq", ".login").strip()


def fetch(repository: str, number: int) -> dict[str, Any]:
    owner, name = repository.split("/", 1)
    answer = json.loads(prs.gh("api", "graphql", "-f", f"query={QUERY}", "-f", f"owner={owner}", "-f", f"name={name}",
                               "-F", f"number={number}"))
    pr = ((answer.get("data") or {}).get("repository") or {}).get("pullRequest")
    if not pr:
        raise ValueError(f"{repository}#{number}: no such pull request ({answer.get('errors', '')})")
    return pr


def author(node: dict[str, Any]) -> str:
    return (node.get("author") or {}).get("login") or "ghost"


def comment(node: dict[str, Any], review: bool = False) -> dict[str, Any]:
    return {
        "id": node["id"],
        "author": author(node),
        "body": (node.get("body") or "").strip(),
        "at": node.get("submittedAt" if review else "createdAt") or "",
        "commit": ((node.get("originalCommit") or {}).get("oid") or "")[:7],
        "url": node.get("url") or "",
        "review": review,
    }


def truncated(pr: dict[str, Any]) -> list[str]:
    return [f"only the first {PAGE} {field} are read" for field in ("reviewThreads", "reviews", "comments")
            if ((pr.get(field) or {}).get("pageInfo") or {}).get("hasNextPage")]


def conversations(pr: dict[str, Any], me: str) -> list[dict[str, Any]]:
    """Inline threads, then review summaries and top-level comments: on the user's own PR each of those is a
    claim of its own; on someone else's they form one conversation, where the user's comments get replies."""
    found = []
    for node in (pr.get("reviewThreads") or {}).get("nodes") or []:
        comments = [comment(item) for item in (node.get("comments") or {}).get("nodes") or []]
        found.append({"id": node["id"], "kind": "inline", "path": node.get("path"), "line": node.get("line") or node.get("originalLine"),
                      "resolved": bool(node.get("isResolved")), "outdated": bool(node.get("isOutdated")),
                      "comments": [item for item in comments if item["body"]]})
    top = [comment(node) for node in (pr.get("comments") or {}).get("nodes") or []]
    top += [comment(node, review=True) for node in (pr.get("reviews") or {}).get("nodes") or []]
    top = sorted((item for item in top if item["body"]), key=lambda item: item["at"])
    if author(pr) == me:
        found += [{"id": item["id"], "kind": "review" if item["review"] else "top", "resolved": False, "comments": [item]} for item in top]
    elif top:
        found.append({"id": "conversation", "kind": "conversation", "resolved": False, "comments": top})
    return [conversation for conversation in found if conversation["comments"]]


def focus(conversation: dict[str, Any], me: str, owner: str) -> dict[str, Any] | None:
    """What in the conversation waits on the user, or None.

    comment: on the user's PR, someone else commented; last is their newest comment.
    reply: on another PR, someone answered the user's latest comment (at anchor); last is the newest answer."""
    comments = conversation["comments"]
    if owner == me:
        others = [item for item in comments if item["author"] != me]
        return {"case": "comment", "anchor": -1, "last": others[-1]["id"]} if others else None
    mine = [index for index, item in enumerate(comments) if item["author"] == me]
    if not mine:
        return None
    replies = [item for item in comments[mine[-1] + 1:] if item["author"] != me]
    return {"case": "reply", "anchor": mine[-1], "last": replies[-1]["id"]} if replies else None


def pending(conversation: dict[str, Any], waiting: dict[str, Any], entry: dict[str, Any] | None) -> bool:
    """Open threads not judged at their newest comment, and any thread with a comment since it was last seen.
    A resolved thread seen for the first time is trusted as done; it comes back with its next comment."""
    if entry is None:
        return not conversation["resolved"]
    return entry.get("last") != waiting["last"]


# Local state --------------------------------------------------------------------------------------------


def state_path(root: Path, identifier: str, number: int) -> Path:
    return root / ".cc-local" / "threads" / f"{identifier}-{number}.json"


def load_state(root: Path, identifier: str, number: int) -> dict[str, dict[str, Any]]:
    return prs.load_json(state_path(root, identifier, number)) or {}


def save_state(root: Path, identifier: str, number: int, state: dict[str, dict[str, Any]]) -> None:
    path = state_path(root, identifier, number)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def today() -> str:
    return datetime.date.today().isoformat()


def select(pr: dict[str, Any], me: str, state: dict[str, dict[str, Any]], everything: bool) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """The conversations to judge, with what waits in each. Resolved threads seen for the first time are
    recorded as seen (no verdict), so a later comment on them is noticed."""
    owner = author(pr)
    chosen = []
    for conversation in conversations(pr, me):
        waiting = focus(conversation, me, owner)
        if not waiting:
            continue
        entry = state.get(conversation["id"])
        if everything or pending(conversation, waiting, entry):
            chosen.append((conversation, waiting))
        elif entry is None:
            state[conversation["id"]] = {"last": waiting["last"], "verdict": None, "at": today()}
    return chosen


def waiting_mark(root: Path, identifier: str, repository: str, number: int, me: str) -> str:
    """The ./cc prs column: what in this PR's conversation waits on the user."""
    pr = fetch(repository, number)
    state = load_state(root, identifier, number)
    chosen = select(pr, me, state, everything=False)
    save_state(root, identifier, number, state)
    if not chosen:
        return ""
    return f"{len(chosen)} to judge" if author(pr) == me else "author replied"


# Prompts --------------------------------------------------------------------------------------------------


def labels(conversation: dict[str, Any], owner: str) -> dict[str, str]:
    names = {owner: "PR author"}
    for item in conversation["comments"]:
        if item["author"] not in names:
            names[item["author"]] = f"Commenter {chr(ord('A') + len(names) - 1)}"
    return names


def anonymize(text: str, names: dict[str, str], everyone: set[str]) -> str:
    """Replace every login of the PR: @mentions always, bare words for logins long enough not to be ordinary words."""
    for name in sorted(everyone, key=len, reverse=True):
        label = names.get(name, "another user")
        text = re.sub(rf"@{re.escape(name)}\b", label, text, flags=re.IGNORECASE)
        if len(name) >= 4:
            text = re.sub(rf"(?<![\w/-]){re.escape(name)}(?![\w-])", label, text, flags=re.IGNORECASE)
    return text


def where(conversation: dict[str, Any]) -> str:
    if conversation["kind"] == "inline":
        return f"{conversation['path']}:{conversation['line'] or '?'}"
    return {"review": "review summary", "top": "top-level comment", "conversation": "top-level conversation"}[conversation["kind"]]


def notes(root: Path) -> str:
    """One line per current CC note, so a sceptic in the PR worktree can check a claim against them."""
    lines = []
    for path in sorted((root / "docs").rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        status = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
        summary = re.search(r"^summary:\s*(.+)$", text, re.MULTILINE)
        if summary and not (status and status.group(1) == "superseded") and path.name != "index.md":
            lines.append(f"- {path.relative_to(root).as_posix()}: {summary.group(1).strip()}")
    return "\n".join(lines) or "(none)"


def thread_prompt(root: Path, identifier: str, pr: dict[str, Any], conversation: dict[str, Any], waiting: dict[str, Any],
                  everyone: set[str], cc_notes: str) -> str:
    names = labels(conversation, author(pr))
    nonce = secrets.token_hex(4)
    location = where(conversation)
    if conversation["kind"] == "inline":
        location = f"`{location}`, an inline review thread" + (" (outdated: the line has changed since)" if conversation["outdated"] else "")
    lines = [
        "# Thread",
        "",
        f"Case: {waiting['case']}",
        f"Pull request: {identifier} #{pr['number']} \"{anonymize(pr.get('title') or '', names, everyone)}\"",
        f"Location: {location}",
        f"State: {'resolved' if conversation['resolved'] else 'unresolved'}",
        f"The current directory is the PR head, commit {(pr.get('headRefOid') or '?')[:7]}.",
        "",
        "## Comments",
    ]
    for index, item in enumerate(conversation["comments"], 1):
        kind = "review summary" if item["review"] else "comment"
        on = f" · on commit {item['commit']}" if item["commit"] else ""
        lines += [
            "",
            f"### {index} · {names[item['author']]} · {kind} · {item['at'][:10]}{on}",
            f"----- BEGIN COMMENT {index} {nonce} -----",
            anonymize(item["body"], names, everyone),
            f"----- END COMMENT {index} {nonce} -----",
        ]
    count = len(conversation["comments"])
    if waiting["case"] == "comment":
        task = ("Judge the claims of the commenters (everyone except the PR author) in this conversation. Where the PR author "
                "has already answered, weigh the answer as evidence, not as proof.")
    else:
        anchor = waiting["anchor"] + 1
        later = f"{anchor + 1}" if anchor + 1 == count else f"{anchor + 1} to {count}"
        task = f"Comment {anchor} is the review comment. Judge whether comment(s) {later} answer it."
    lines += ["", "## What to judge", "", task, "", "# CC notes", "", cc_notes]
    return "\n".join(lines)


def role_prompt(root: Path, role: dict[str, Any], body: str) -> str:
    return "\n\n".join([*(skill_text(root, skill) for skill in role.get("skills", [])), body])


def judge_prompt(body: str, replies: list[str | None]) -> tuple[str, list[int]]:
    """The thread and the sceptics' replies as Review A, B, ... in random order; returns the order used."""
    order = list(range(len(replies)))
    random.SystemRandom().shuffle(order)
    reviews = [f"## Review {chr(ord('A') + label)}\n\n{replies[index] or '(no usable verdict)'}" for label, index in enumerate(order)]
    return body + "\n\n# Reviews\n\n" + "\n\n".join(reviews), order


# Verdicts -------------------------------------------------------------------------------------------------


def parse(text: str | None, case: str) -> dict[str, Any] | None:
    """VERDICT: <tag>, EVIDENCE: lines, REPLY: text. None when the tag is unknown for the case, or a verdict
    that rests on the code comes without evidence."""
    match = re.match(r"\s*VERDICT:\s*([A-Z][A-Z-]*)", text or "")
    if not match or match.group(1) not in VERDICTS[case]:
        return None
    tag = match.group(1)
    section = re.search(r"^EVIDENCE:\s*$(.*?)(?=^REPLY:|\Z)", text, re.MULTILINE | re.DOTALL)
    evidence = re.findall(r"^\s*-\s+(.+?)\s*$", section.group(1) if section else "", re.MULTILINE)
    reply = re.search(r"^REPLY:\s*(.*)\Z", text, re.MULTILINE | re.DOTALL)
    if not evidence and tag not in UNEVIDENCED:
        return None
    # Models sometimes append notes after the reply, behind a rule; they are not part of the draft.
    draft = re.split(r"^-{3,}\s*$", reply.group(1), maxsplit=1, flags=re.MULTILINE)[0] if reply else ""
    return {"verdict": tag, "evidence": evidence, "reply": draft.strip()}


def agree(verdicts: list[dict[str, Any] | None]) -> dict[str, Any] | None:
    """The shared verdict when every sceptic gave one and they are the same; None is a split."""
    if not verdicts or any(verdict is None for verdict in verdicts) or len({verdict["verdict"] for verdict in verdicts}) != 1:
        return None
    best = max(verdicts, key=lambda verdict: len(verdict["evidence"]))
    evidence = list(dict.fromkeys(line for verdict in verdicts for line in verdict["evidence"]))
    return {"verdict": verdicts[0]["verdict"], "evidence": evidence, "reply": best["reply"]}


# Running ---------------------------------------------------------------------------------------------------


class Judging:
    """One ./cc prs judge run: calls the roles, reports to the event stream, keeps one Cursor snapshot."""

    def __init__(self, root: Path, worktree: Path, roles: dict[str, dict[str, Any]], stream: events.Events):
        self.root, self.worktree, self.roles, self.events = root, worktree, roles, stream
        self.logs = stream.path.parent / "logs"
        self.lock = threading.Lock()
        self.working: dict[str, Path] = {}
        self.shared: Path | None = None
        self.before: dict[str, tuple[int, int]] = {}
        if any(role["provider"] == "cursor" for role in roles.values()):
            self.shared, self.before = providers.snapshot(worktree)

    def activity(self) -> dict[str, tuple[float, str]]:
        with self.lock:
            return {who: events.file_activity(log) for who, log in self.working.items()}

    def call(self, identifier: str, body: str, name: str) -> str | None:
        """The role's reply, or None when the call failed (it then counts as no usable verdict)."""
        role = self.roles[identifier]
        log = self.logs / f"{name}.log"
        who = f"{identifier} ({role['provider']} {role['model']}) on {name}"
        self.events.emit("agent", f"{who} started", who=identifier)
        with self.lock:
            self.working[who] = log
        try:
            return providers.run(role, role_prompt(self.root, role, body), self.worktree, log, timeout=TIMEOUT,
                                 on_say=lambda text: self.events.emit("say", f"{identifier}: {text}", who=identifier),
                                 shared=self.shared if role["provider"] == "cursor" else None)
        except providers.ProviderError as error:
            self.events.emit("error", str(error), who=identifier)
            return None
        finally:
            with self.lock:
                self.working.pop(who, None)
            self.events.emit("agent", f"{who} finished", who=identifier)

    def tampered(self) -> bool:
        """Fail closed: a write in the shared Cursor snapshot voids the Cursor replies made in it; start a fresh one."""
        if self.shared is None or providers.fingerprint(self.shared) == self.before:
            return False
        self.events.emit("error", "a Cursor role changed its read-only snapshot; its verdicts are void")
        shutil.rmtree(self.shared, ignore_errors=True)
        self.shared, self.before = providers.snapshot(self.worktree)
        return True

    def close(self) -> None:
        if self.shared is not None:
            shutil.rmtree(self.shared, ignore_errors=True)


def council(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    path = root / "catalog" / "councils" / "threads.json"
    if not path.is_file():
        raise ValueError("add council threads (templates/councils/threads.json) to catalog/councils, with its roles from templates/agents")
    config = prs.load_json(path)
    names = [*config.get("sceptics", []), *([config["judge"]] if config.get("judge") else [])]
    roles = {}
    for name in names:
        role = prs.load_json(root / "catalog" / "agents" / f"{name}.json")
        if not role:
            raise ValueError(f"council threads names role {name}, but catalog/agents/{name}.json is missing")
        available, detail = providers.login_status(role["provider"])
        if not available:
            raise ValueError(f"role {name} needs {role['provider']}: {detail}")
        roles[name] = role
    return config, roles


def review_worktree(root: Path, identifier: str, number: int) -> Path:
    prs.checkout(root, identifier, number)
    layout = prs.load_json(root / "control-center.json")["layout"]
    return (root / layout["worktrees"]).resolve() / f"pr-{identifier}-{number}" / f"{identifier}_wt"


def judge(root: Path, identifier: str, number: int, everything: bool) -> dict[str, Any]:
    config, roles = council(root)
    sceptics, referee = config["sceptics"], config.get("judge")
    repository = prs.slug(root, identifier)
    me = login()
    pr = fetch(repository, number)
    state = load_state(root, identifier, number)
    chosen = select(pr, me, state, everything)
    result = {"repo": identifier, "number": number, "title": pr.get("title", ""), "url": pr.get("url", ""),
              "warnings": truncated(pr), "threads": []}
    if not chosen:
        save_state(root, identifier, number, state)
        return result
    worktree = review_worktree(root, identifier, number)
    stream, owned = events.own_stream(root, f"threads-{identifier}-{number}")
    if owned:
        stream.emit("start", f"judging {len(chosen)} thread(s) of {identifier} #{number}", pid=os.getpid())
    run = Judging(root, worktree, roles, stream)
    watchdog = events.Watchdog(stream, run.activity)
    watchdog.start()
    everyone = {me, author(pr), *(item["author"] for conversation, _ in chosen for item in conversation["comments"])}
    cc_notes = notes(root)
    try:
        bodies = [thread_prompt(root, identifier, pr, conversation, waiting, everyone, cc_notes) for conversation, waiting in chosen]
        stream.emit("step", f"sceptics: {', '.join(sceptics)} on {len(chosen)} thread(s)")
        with concurrent.futures.ThreadPoolExecutor(PARALLEL) as pool:
            futures = {(index, name): pool.submit(run.call, name, body, f"{index:02d}-{name}")
                       for index, body in enumerate(bodies, 1) for name in sceptics}
            replies = {key: future.result() for key, future in futures.items()}
        if run.tampered():
            replies = {key: None if roles[key[1]]["provider"] == "cursor" else reply for key, reply in replies.items()}
        verdicts = {key: parse(reply, chosen[key[0] - 1][1]["case"]) for key, reply in replies.items()}

        finals: dict[int, dict[str, Any] | None] = {}
        settled: set[int] = set()
        for index in range(1, len(chosen) + 1):
            mine = [verdicts[(index, name)] for name in sceptics]
            finals[index] = mine[0] if len(sceptics) == 1 else agree(mine)
        split = [index for index in finals if finals[index] is None and len(sceptics) > 1 and referee]
        if split:
            stream.emit("step", f"judge: {referee} on {len(split)} split thread(s)")
            prompts = {index: judge_prompt(bodies[index - 1], [replies[(index, name)] for name in sceptics]) for index in split}
            # Who wrote which review stays out of the prompt; the user can read it in the run's labels.json.
            (run.logs.parent / "labels.json").parent.mkdir(parents=True, exist_ok=True)
            (run.logs.parent / "labels.json").write_text(json.dumps(
                {chosen[index - 1][0]["id"]: {chr(ord("A") + label): sceptics[source] for label, source in enumerate(order)}
                 for index, (_, order) in prompts.items()}, indent=2) + "\n", encoding="utf-8")
            with concurrent.futures.ThreadPoolExecutor(PARALLEL) as pool:
                futures = {index: pool.submit(run.call, referee, prompt, f"{index:02d}-{referee}") for index, (prompt, _) in prompts.items()}
                judged = {index: future.result() for index, future in futures.items()}
            void = run.tampered() and roles[referee]["provider"] == "cursor"
            for index in split:
                settled.add(index)
                finals[index] = None if void else parse(judged[index], chosen[index - 1][1]["case"])

        for index, (conversation, waiting) in enumerate(chosen, 1):
            final = finals[index]
            entry = {
                "thread": conversation["id"],
                "case": waiting["case"],
                "where": where(conversation),
                "url": conversation["comments"][waiting["anchor"] + 1 if waiting["case"] == "reply" else -1]["url"],
                "verdict": final["verdict"] if final else UNJUDGED,
                "split": index in settled,
                "sceptics": {name: (verdicts[(index, name)] or {}).get("verdict", "unparsed") for name in sceptics},
                "evidence": final["evidence"] if final else [],
                "reply": final["reply"] if final else "",
                "logs": str(run.logs),
            }
            result["threads"].append(entry)
            stream.emit("gate" if final else "warn", f"{entry['where']}: {entry['verdict']}" + (" (split)" if entry["split"] else ""))
            if final:
                state[conversation["id"]] = {"last": waiting["last"], "verdict": final["verdict"], "at": today()}
        save_state(root, identifier, number, state)
    finally:
        watchdog.stopped.set()
        run.close()
        if owned:
            unjudged = sum(entry["verdict"] == UNJUDGED for entry in result["threads"])
            stream.emit(events.END, f"judged {len(result['threads']) - unjudged} of {len(chosen)} thread(s)", ok=not unjudged)
    return result


# Output ------------------------------------------------------------------------------------------------------


ORDER = [*VERDICTS["comment"], *VERDICTS["reply"], UNJUDGED]


def report(result: dict[str, Any]) -> str:
    threads = sorted(result["threads"], key=lambda entry: ORDER.index(entry["verdict"]))
    lines = [f"{result['repo']} #{result['number']} · {result['title']}"]
    if not threads:
        return "\n".join(lines + ["nothing waits on you: no thread to judge (--all re-judges every thread)"])
    counts = {tag: sum(entry["verdict"] == tag for entry in threads) for tag in ORDER}
    split = sum(entry["split"] for entry in threads)
    lines.append(f"{len(threads)} thread(s): " + " · ".join(f"{tag} {count}" for tag, count in counts.items() if count)
                 + (f" ({split} split)" if split else ""))
    for entry in threads:
        mark = ""
        if entry["split"]:
            mark = " · split (" + ", ".join(f"{name} {tag}" for name, tag in entry["sceptics"].items()) + ")"
        lines += ["", f"{entry['verdict']} · {entry['where']}{mark} · {entry['url']}"]
        lines += [f"  - {line}" for line in entry["evidence"]]
        if entry["reply"]:
            lines.append("  reply: " + entry["reply"].replace("\n", "\n         "))
        if entry["verdict"] == UNJUDGED:
            lines.append(f"  no usable verdict; logs: {entry['logs']}")
    lines += [f"warning: {warning}" for warning in result["warnings"]]
    return "\n".join(lines)


def listing(root: Path, identifier: str, number: int, everything: bool) -> dict[str, Any]:
    """What a judge run would send: the selected threads with their anonymized prompts."""
    me = login()
    pr = fetch(prs.slug(root, identifier), number)
    state = load_state(root, identifier, number)
    chosen = select(pr, me, state, everything)
    everyone = {me, author(pr), *(item["author"] for conversation, _ in chosen for item in conversation["comments"])}
    cc_notes = notes(root)
    return {"repo": identifier, "number": number, "warnings": truncated(pr), "threads": [
        {"thread": conversation["id"], "case": waiting["case"], "where": where(conversation), "comments": len(conversation["comments"]),
         "prompt": thread_prompt(root, identifier, pr, conversation, waiting, everyone, cc_notes)}
        for conversation, waiting in chosen]}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=f"./cc prs {argv[1]}")
    parser.add_argument("root", type=Path)
    parser.add_argument("command", choices=("threads", "judge"))
    parser.add_argument("repository", help="catalog id")
    parser.add_argument("number", type=int)
    parser.add_argument("--all", action="store_true", help="every thread, not only those waiting since the last judgment")
    parser.add_argument("--json", action="store_true", help="machine-readable, for skills")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "threads":
            result = listing(root, args.repository, args.number, args.all)
            text = "\n".join([f"{entry['case']:<8} {entry['where']}  ({entry['comments']} comment(s))" for entry in result["threads"]]
                             or ["nothing waits on you"])
        else:
            result = judge(root, args.repository, args.number, args.all)
            text = report(result)
    except (ValueError, OSError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else text)
    return 0

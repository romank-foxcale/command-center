#!/usr/bin/env python3
"""./cc prs learn: the review comments that were accepted on merged PRs of the catalog repos, as raw material
for review lessons (docs/lessons/, templates/lesson.md).

A comment counts as accepted, without any model call, when:
- it is an inline thread started by someone other than the PR author, and its line changed before merge
  (GitHub marks the thread outdated); or
- ./cc prs judge judged its thread VALID (.cc-local/threads/), which also covers summaries and top-level comments.

People are anonymized as in ./cc prs judge, and only "human" or "bot" is kept about an author. Comment text
lives in memory and on stdout only. Local state (.cc-local/lessons/<repo>.json) keeps the newest merge
time and PR number processed, and when the harvest ran: never comment bodies."""

from __future__ import annotations

import argparse
import datetime
import json
import re
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prs  # noqa: E402
import threads  # noqa: E402
from threads import providers  # noqa: E402

BACKFILL = 50
LEARNER = "review-learner"
LESSONS = "docs/lessons"
ROUTES = ("note", "gate")
LIMIT = 500
PAGE = threads.PAGE
QUERY = """query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number title url mergedAt author { login }
      reviewThreads(first: %(page)d) {
        pageInfo { hasNextPage }
        nodes {
          id isResolved isOutdated path line originalLine
          comments(first: %(page)d) { nodes { id author { login __typename } body createdAt url diffHunk } }
        }
      }
      reviews(first: %(page)d) { pageInfo { hasNextPage } nodes { id author { login __typename } body submittedAt url } }
      comments(first: %(page)d) { pageInfo { hasNextPage } nodes { id author { login __typename } body createdAt url } }
    }
  }
}""" % {"page": PAGE}


# GitHub data -------------------------------------------------------------------------------------------


def merged(repository: str, since: str | None) -> list[dict[str, Any]]:
    """Merged PRs, oldest merge first. With a date, every PR merged on or after it; without, the last BACKFILL."""
    search = ["--search", f"merged:>={since[:10]}", "--limit", str(LIMIT)] if since else ["--limit", str(BACKFILL)]
    rows = json.loads(prs.gh("pr", "list", "--repo", repository, "--state", "merged", "--json", "number,mergedAt", *search) or "[]")
    return sorted(rows, key=lambda row: (row["mergedAt"], row["number"]))


def fetch(repository: str, number: int) -> dict[str, Any]:
    owner, name = repository.split("/", 1)
    answer = json.loads(prs.gh("api", "graphql", "-f", f"query={QUERY}", "-f", f"owner={owner}", "-f", f"name={name}",
                               "-F", f"number={number}"))
    pr = ((answer.get("data") or {}).get("repository") or {}).get("pullRequest")
    if not pr:
        raise ValueError(f"{repository}#{number}: no such pull request ({answer.get('errors', '')})")
    return pr


def kind(node: dict[str, Any]) -> str:
    who = node.get("author") or {}
    return "bot" if who.get("__typename") == "Bot" or (who.get("login") or "").endswith("[bot]") else "human"


# Selection ----------------------------------------------------------------------------------------------


def judged_valid(root: Path, identifier: str, number: int) -> set[str]:
    return {thread for thread, entry in threads.load_state(root, identifier, number).items()
            if (entry or {}).get("verdict") == "VALID"}


def accepted(pr: dict[str, Any], valid: set[str]) -> list[dict[str, Any]]:
    """The accepted comments of one merged PR, with the logins still in them (see anonymized)."""
    owner = threads.author(pr)
    found = []
    for node in (pr.get("reviewThreads") or {}).get("nodes") or []:
        comments = [item for item in (node.get("comments") or {}).get("nodes") or [] if (item.get("body") or "").strip()]
        if not comments or threads.author(comments[0]) == owner:
            continue
        source = "valid" if node["id"] in valid else "outdated" if node.get("isOutdated") else None
        if source:
            found.append({"thread": node["id"], "source": source, "where": f"{node.get('path')}:{node.get('line') or node.get('originalLine') or '?'}",
                          "url": comments[0].get("url") or "", "author": kind(comments[0]), "hunk": comments[0].get("diffHunk") or "",
                          "comments": [(threads.author(item), item["body"].strip()) for item in comments]})
    tops = [(node, "review summary") for node in (pr.get("reviews") or {}).get("nodes") or []]
    tops += [(node, "top-level comment") for node in (pr.get("comments") or {}).get("nodes") or []]
    for node, where in tops:
        if node["id"] in valid and (node.get("body") or "").strip():
            found.append({"thread": node["id"], "source": "valid", "where": where, "url": node.get("url") or "", "author": kind(node),
                          "hunk": "", "comments": [(threads.author(node), node["body"].strip())]})
    return found


def anonymized(item: dict[str, Any], owner: str) -> dict[str, Any]:
    """Logins become "PR author" and "Reviewer A", "Reviewer B", ...; the body keeps who said what, never who."""
    names = {owner: "PR author"}
    for who, _ in item["comments"]:
        names.setdefault(who, f"Reviewer {chr(ord('A') + len(names) - 1)}")
    everyone = set(names)
    lines = [f"{names[who]}: {threads.anonymize(body, names, everyone)}" for who, body in item["comments"]]
    return {**{key: value for key, value in item.items() if key != "comments"}, "text": "\n".join(lines)}


# Local state --------------------------------------------------------------------------------------------


def state_path(root: Path, identifier: str) -> Path:
    return root / ".cc-local" / "lessons" / f"{identifier}.json"


def remember(root: Path, result: dict[str, Any]) -> None:
    """Move the repo's saved position to the newest merge harvested; done only once the run succeeded."""
    if not result.get("position"):
        return
    path = state_path(root, result["repo"])
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    path.write_text(json.dumps({**result["position"], "harvested_at": stamp}, indent=2) + "\n", encoding="utf-8")


# Harvest --------------------------------------------------------------------------------------------------


def harvest(root: Path, identifier: str, since: str | None) -> dict[str, Any]:
    """One repo: the PRs merged since the last harvest (or --since), and their accepted comments. The saved
    position moves only through remember(), after the learner has used them."""
    repository = prs.slug(root, identifier)
    last = prs.load_json(state_path(root, identifier)) or {}
    start = since or last.get("merged_at")
    rows = merged(repository, start)
    complete = len(rows)
    if not since and last:
        rows = [row for row in rows if (row["mergedAt"], row["number"]) > (last["merged_at"], last["pr"])]
    result: dict[str, Any] = {"repo": identifier, "since": start, "prs": [], "warnings": []}
    if start and complete >= LIMIT:
        result["warnings"].append(f"only the newest {LIMIT} PRs merged since {start[:10]} are read; harvest again with a later --since")
    for row in rows:
        pr = fetch(repository, row["number"])
        items = [anonymized(item, threads.author(pr)) for item in accepted(pr, judged_valid(root, identifier, row["number"]))]
        result["prs"].append({"number": row["number"], "url": pr.get("url", ""), "merged_at": row["mergedAt"], "accepted": items})
        result["warnings"] += [f"#{row['number']}: {warning}" for warning in threads.truncated(pr)]
    if rows and not since:
        result["position"] = {"merged_at": rows[-1]["mergedAt"], "pr": rows[-1]["number"]}
    return result


# Learner ---------------------------------------------------------------------------------------------------


def known_lessons(root: Path) -> dict[str, dict[str, Any]]:
    """The current lessons: path -> summary and repos. Superseded and archived ones are not matched against."""
    found = {}
    for path in sorted((root / LESSONS).glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        status = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
        if path.name == "index.md" or (status and status.group(1) in ("superseded", "archived")):
            continue
        summary = re.search(r"^summary:\s*(.+)$", text, re.MULTILINE)
        repos = re.search(r"^repos:\s*\n((?:\s+-\s+.+\n)+)", text, re.MULTILINE)
        found[path.relative_to(root).as_posix()] = {
            "summary": summary.group(1).strip() if summary else "",
            "repos": re.findall(r"-\s+(\S+)", repos.group(1)) if repos else [],
        }
    return found


def keyed(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Every accepted comment of the run under a key such as api#12/T1, the only handle the learner gets."""
    return {f"{result['repo']}#{pr['number']}/{item['thread']}": {**item, "repo": result["repo"]}
            for result in results for pr in result["prs"] for item in pr["accepted"]}


def learner_prompt(comments: dict[str, dict[str, Any]], lessons: dict[str, dict[str, Any]]) -> str:
    nonce = secrets.token_hex(4)
    lines = ["# Accepted comments"]
    for key, item in comments.items():
        lines += ["", f"## {key} · {item['where']} · {item['author']} · {item['source']}"]
        if item["hunk"]:
            lines += ["", "```diff", item["hunk"], "```"]
        lines += [f"----- BEGIN COMMENT {key} {nonce} -----", item["text"], f"----- END COMMENT {key} {nonce} -----"]
    lines += ["", "# Existing lessons", ""]
    lines += [f"- {path} (repos: {', '.join(lesson['repos']) or '?'}): {lesson['summary']}" for path, lesson in lessons.items()] or ["(none)"]
    return "\n".join(lines)


def parse(text: str | None, comments: dict[str, dict[str, Any]], lessons: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    """The learner's JSON, kept only where it holds: known comment keys and lesson paths, a valid route, at least
    two unmatched supporting comments per candidate. Permalinks come from the harvest, never from the model."""
    blocks = re.findall(r"```(?:json)?\s*\n(.*?)```", text or "", re.DOTALL)
    try:
        data = json.loads(blocks[-1] if blocks else (text or "").strip())
    except json.JSONDecodeError as error:
        raise ValueError(f"the review learner gave no usable JSON: {error}") from error
    if not isinstance(data, dict):
        raise ValueError("the review learner gave no usable JSON object")
    warnings, matches, matched = [], [], set()
    for entry in data.get("matches") or []:
        entry = entry if isinstance(entry, dict) else {}
        key, lesson = entry.get("comment"), entry.get("lesson")
        if key not in comments or lesson not in lessons or key in matched:
            warnings.append(f"match dropped: {key} -> {lesson}")
            continue
        matched.add(key)
        matches.append({"comment": key, "lesson": lesson, "url": comments[key]["url"]})
    candidates, used = [], set()
    for entry in data.get("candidates") or []:
        entry = entry if isinstance(entry, dict) else {}
        keys = [key for key in dict.fromkeys(entry.get("comments") or [])
                if key in comments and key not in matched and key not in used]
        problem = ("fewer than two usable supporting comments" if len(keys) < 2
                   else "route must be note or gate" if entry.get("route") not in ROUTES
                   else "a gate route needs a check_idea" if entry.get("route") == "gate" and not entry.get("check_idea")
                   else "missing title or statement" if not entry.get("title") or not entry.get("statement") else "")
        if problem:
            warnings.append(f"candidate dropped: {entry.get('title') or entry.get('id') or '?'}: {problem}")
            continue
        used.update(keys)
        sources = {comments[key]["repo"] for key in keys}
        candidates.append({
            "id": str(entry.get("id") or ""), "title": entry["title"], "statement": entry["statement"],
            "repos": sorted(set(entry.get("repos") or []) & sources) or sorted(sources),
            "route": entry["route"], "check_idea": entry.get("check_idea") or "",
            "evidence": [comments[key]["url"] for key in keys], "comments": keys,
        })
    return {"matches": matches, "candidates": candidates}, warnings


def repeats(learned: dict[str, Any], accepted: int) -> dict[str, Any]:
    """The repeat-offence count: accepted comments that a known lesson should already have prevented."""
    per_lesson: dict[str, int] = {}
    for match in learned["matches"]:
        per_lesson[match["lesson"]] = per_lesson.get(match["lesson"], 0) + 1
    return {"matched": len(learned["matches"]), "accepted": accepted, "per_lesson": per_lesson}


def learner(root: Path) -> dict[str, Any]:
    role = prs.load_json(root / "catalog" / "agents" / f"{LEARNER}.json")
    if not role:
        raise ValueError(f"catalog/agents/{LEARNER}.json is missing; copy it from templates/agents")
    return role


def learn(root: Path, results: list[dict[str, Any]]) -> dict[str, Any]:
    """One learner call over every accepted comment of the run. Its log holds comment text, so it lives in a
    temporary directory that is removed afterwards."""
    comments = keyed(results)
    lessons = known_lessons(root)
    role = learner(root)
    with tempfile.TemporaryDirectory(prefix="cc-lessons-") as temporary:
        reply = providers.run(role, threads.role_prompt(root, role, learner_prompt(comments, lessons)), root,
                              Path(temporary) / "learner.log", timeout=threads.TIMEOUT)
    learned, warnings = parse(reply, comments, lessons)
    return {**learned, "repeats": repeats(learned, len(comments)), "warnings": warnings,
            "learner": f"{role['provider']} {role['model']}"}


# Output ------------------------------------------------------------------------------------------------------


def report(result: dict[str, Any]) -> str:
    total = sum(len(pr["accepted"]) for pr in result["prs"])
    lines = [f"{result['repo']}: {len(result['prs'])} merged PR(s) since {result['since'] or f'the last {BACKFILL}'}, {total} accepted comment(s)"]
    for pr in result["prs"]:
        lines.append(f"  #{pr['number']}  {len(pr['accepted'])} accepted  {pr['url']}")
        for item in pr["accepted"]:
            lines.append(f"    {item['source']:<8} {item['author']:<5} {item['where']}  {item['url']}")
    lines += [f"  warning: {warning}" for warning in result["warnings"]]
    return "\n".join(lines)


def render(output: dict[str, Any]) -> str:
    lines = [report(result) for result in output["repos"]] or ["no catalog repo on GitHub"]
    learned = output["learned"]
    if learned:
        counts = learned["repeats"]
        lines += ["", f"review learner ({learned['learner']}): {counts['matched']} of {counts['accepted']} accepted comment(s) repeat a known lesson"]
        lines += [f"  {count}  {lesson}" for lesson, count in sorted(counts["per_lesson"].items(), key=lambda item: -item[1])]
        for candidate in learned["candidates"]:
            lines += ["", f"candidate ({candidate['route']}) · {candidate['title']} · repos: {', '.join(candidate['repos'])}",
                      f"  {candidate['statement']}"]
            lines += [f"  check: {candidate['check_idea']}"] if candidate["check_idea"] else []
            lines += [f"  - {url}" for url in candidate["evidence"]]
        lines += [f"warning: {warning}" for warning in learned["warnings"]]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="./cc prs learn")
    parser.add_argument("root", type=Path)
    parser.add_argument("command", choices=("learn",))
    parser.add_argument("repositories", nargs="*", help="catalog ids; all catalog repos with a GitHub remote by default")
    parser.add_argument("--since", help="YYYY-MM-DD: harvest every PR merged since then, without moving the saved position")
    parser.add_argument("--harvest-only", action="store_true", help="list the accepted comments without calling the review learner")
    parser.add_argument("--json", action="store_true", help="machine-readable, with the anonymized comment text, for skills")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.since and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.since):
        print("error: --since must use YYYY-MM-DD", file=sys.stderr)
        return 2
    identifiers = args.repositories or [name for name, entry in prs.catalog(root).items()
                                        if prs.GITHUB.search(str(entry.get("remote", "")))]
    results, failed = [], 0
    for identifier in identifiers:
        try:
            results.append(harvest(root, identifier, args.since))
        except (ValueError, OSError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
            print(f"error: {identifier}: {error}", file=sys.stderr)
            failed += 1
    learned = None
    if not args.harvest_only and any(pr["accepted"] for result in results for pr in result["prs"]):
        try:
            learned = learn(root, results)
        except (ValueError, OSError, providers.ProviderError, subprocess.TimeoutExpired) as error:
            print(f"error: {error}; the saved positions did not move, so the next run sees these comments again", file=sys.stderr)
            failed += 1
            results = [{**result, "position": None} for result in results]
    for result in results:
        remember(root, result)
    output = {"repos": results, "learned": learned}
    print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else render(output))
    return 1 if failed else 0

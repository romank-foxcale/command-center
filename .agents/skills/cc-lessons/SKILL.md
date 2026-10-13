---
name: cc-lessons
description: Learn from past PR reviews with ./cc prs learn - harvest the review comments accepted on merged catalog PRs, show how many repeat a known lesson, and turn recurring shortcomings into team-level lesson notes in docs/lessons/, each only after the user confirms it. Use when the user wants the CC to learn from reviews, asks what reviewers keep pointing out, or asks whether past lessons are working.
---

# CC lessons

First read `../_shared/cc-cli.md` and follow it.

A lesson is a recurring shortcoming reviewers raised, written as a rule a diff can be checked against (`templates/lesson.md`). `cc-review` cites lessons as `[KNOWLEDGE]` findings, so a confirmed lesson is checked on every later review. Lessons are about the code and the team's practice, never about a person.

## 1. Harvest

Run `./cc prs learn [<repo>...] --json` (all catalog repos on GitHub by default). It reads the PRs merged since the last run (the last 50 on a first run), keeps the comments that were accepted, and passes them to the `review-learner` agent. That agent's provider and model are set in `./cc settings`, under Agents.

- `--since YYYY-MM-DD` re-reads from a date without moving the saved position. Use it only when the user asks to look further back.
- `--harvest-only` lists the accepted comments without calling the learner. Use it when the user only wants to see them.
- If it fails because `catalog/agents/review-learner.json` is missing, or the provider isn't logged in, say so and stop. The saved position did not move, so nothing is lost.

## 2. Report

```
<n> merged PR(s) · <accepted> accepted comment(s) · <matched> repeat a known lesson
  <count>  docs/lessons/<lesson>.md
Candidates
1. (<route>) <title> · repos: <repos> · <k> comments
   <statement>
   check: <check_idea>            (gate route only)
   - <permalink>
```

- The repeat count is the measure of whether lessons work: a lesson that keeps matching isn't being applied. Say so, and if its route is `note`, ask whether it should become a gate check.
- Relay the command's warnings (truncated PRs, entries the learner got wrong) in one line each.
- No candidates and no matches is a normal result. Say it plainly.

## 3. Confirm, then write

Take the candidates one at a time, as a choice: **write it**, **edit it**, or **skip it**.

- **Write**: check `docs/lessons/` for a note that already states it. If one does, offer to update that note instead. Otherwise draft the note from `templates/lesson.md`:
  - `id`: the candidate's id, or `lessons.<short-name>`.
  - `repos`: the candidate's repos.
  - `occurrences`: the number of supporting comments.
  - `last_seen`: today.
  - `route`: the candidate's route.
  - `evidence`: the permalinks.
  - `relations`: `docs/lessons/index.md`.
  - Body: the statement, its limits, and for `gate` the check idea.

  Show the full draft and its index line, and write it only after the user's yes. Then add the line to `docs/lessons/index.md`.
- **Matches**: for each lesson with matches, offer one update: add the matches to `occurrences`, set `last_seen` to today, and add their permalinks to `evidence`. Write it only after the user's yes.
- After any write, run `./cc validate` and fix what it reports in the note.

## 4. Gate route

For a lesson written or matched with `route: gate`, offer to start a feature that adds the check to the project repo: worktree and verification through `cc-worktree` and `cc-verify`, with a council or a normal edit. Don't start it unasked. Once the check exists and `./cc verify` passes, add the check's path or permalink to the lesson's `evidence`.

## Never

- Write or update a lesson without the user's yes, or write several on one yes the user didn't give for all of them.
- Name, profile or quote a person: no logins, and no "Reviewer A tends to...".
- Store comment text beyond the lesson's own wording, or edit `.cc-local/` by hand.
- Change a project repo from this skill, post to GitHub, commit or push.

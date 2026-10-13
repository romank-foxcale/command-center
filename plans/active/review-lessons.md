# review-lessons: Learn recurring shortcomings from accepted PR review comments

Lifecycle: active
Planning status: accepted

## Outcome

A CC turns review comments that were accepted on merged PRs of its catalog repos into user-confirmed, team-level lessons. Reviews, councils and the Nix gates then apply those lessons before the next PR is pushed. Each harvest reports how many newly accepted comments repeat a known lesson (the repeat-offence count).

## Non-goals

- No per-person reviewer profiles, and no logins in prompts, notes or local state.
- No posting to GitHub. No automatic edits to project repos: a gate check is only offered as a separate feature.
- No scheduled or background harvesting. Harvesting is manual only.
- No change to `./cc prs judge`, its verdicts or the threads council.
- No persisted comment bodies anywhere, `.cc-local/` included.

## Evidence and current behavior

- `scripts/threads.py` fetches review threads through GraphQL (`QUERY`, `fetch`, `conversations`). It gets `isResolved`, `isOutdated`, `path`, `line` and `originalLine`, and anonymizes people (`labels`, `anonymize`). Its local state keeps only thread ids and verdicts (`.cc-local/threads/<repo>-<n>.json`, kit decision 0015).
- `cc-review` already loads CC notes about the repo and reports `[KNOWLEDGE]` findings citing them (`.agents/skills/cc-review/SKILL.md`, kit decision 0012). The `thread-sceptic` role reads a one-line summary per note (`threads.notes`).
- Agents in `templates/agents/*.json` are copied to `catalog/agents/`, and the `./cc settings` Agents tab lists every one of them (`scripts/settings/state.py:111`). So a new agent's provider and model are user-selectable with no settings code change.
- `./cc eval` is a synthetic A/B harness over a fixture CC with headless `claude -p` runs (`scripts/eval/run.py`, kit decision 0019). It never reads real PRs, so it can prove the wiring but cannot measure repeat offences.
- Note kinds live in `docs/{decisions,debt,hacks,projects,glossary}/` and ship empty in the template (kit decision 0017). The `cc-learn` kind table names them.
- This repository is the kit, so the feature ships to every CC. The project folders `docs/lessons/` and `plans/` stay empty here.

## Affected scope

| Repository | Worktree | Read/write | Interfaces |
| --- | --- | --- | --- |
| this CC kit (command-center) | none (CC change on a branch) | write | `./cc prs learn`, `catalog/agents/review-learner.json`, `docs/lessons/` note kind, `cc-lessons` skill, `cc-review` knowledge step, eval scenario |
| catalog project repos | none | read (GitHub API only) | merged PRs and review threads via `gh` |

## Invariants and decisions

- **Accepted comment** (deterministic, no model call): an inline review thread on a merged PR whose commented line changed before merge (`isOutdated` at merge). A thread that `./cc prs judge` marked `VALID` in `.cc-local/threads/` is accepted too. Comments with no line (summaries, top-level comments) count only when judged `VALID`. Comments from both humans and bots count, tagged only as `human` or `bot`.
- **Scope:** merged PRs of catalog repos, by any author. Lessons are team- or repo-level.
- **Anonymity:** comment bodies pass through `threads.anonymize` before any model sees them, the same as kit decision 0015.
- **No stored conversations:** comment text lives only in memory during a run. `.cc-local/lessons/<repo>.json` keeps only the last processed merged PR number and harvest timestamps. Lesson notes keep the statement in the agent's own words, plus thread permalinks as evidence.
- **Review learner agent:** `review-learner` is defined in `templates/agents/review-learner.json` (read-only, default provider `claude`) with its role in `.agents/roles/review-learner/`. The user changes its model in `./cc settings` → Agents. It gets the anonymized accepted comments, the code context (path, diff hunk) and the summaries of the existing `docs/lessons/` notes. It returns JSON with:
  - `matches`: a comment and the existing lesson it repeats;
  - `candidates`: title, statement, repos, `route` (`note` or `gate`), `check_idea` when the route is `gate`, and supporting thread permalinks. A candidate needs at least two supporting threads.
- **Lesson kind:** `docs/lessons/<id>.md` with `docs/lessons/index.md`, linked from `docs/index.md`. Frontmatter is the standard note frontmatter plus `repos`, `occurrences`, `last_seen` and `route` (`note` or `gate`). Evidence holds thread permalinks and, once it exists, the gate check that enforces the lesson.
- **Confirmation:** a lesson is written, or its `occurrences` bumped, only after the user says yes to each one. This is the same contract as `cc-learn`.
- **Gate route:** a `route: gate` lesson leads to an offer to start a normal feature (`cc-worktree` plus a council or an edit) that adds the check to the project repo. The harvest never writes to project repos.
- **Harvest:** `./cc prs learn [<repo>] [--since <date>] [--json]` is manual and incremental. A first run without state backfills the last 50 merged PRs.
- **Repeat-offence count:** each run reports `matched / accepted` overall and per lesson.
- **Kit decision 0020** records this mechanism, linked from 0012 and 0015.

## Open questions

| Question | Impact | Owner/next evidence |
| --- | --- | --- |
| Is `isOutdated` at merge time a good enough proxy for "the comment led to a change"? A force-push or rebase can mark untouched threads outdated. | False accepted comments add noise to candidates. The two-thread minimum and user confirmation limit the damage. | WP2: measure on one real catalog repo and compare against a hand-checked sample of 20 threads. If precision is below ~70%, also require a commit after the comment that touches `path`. |
| GraphQL page limits for PRs with many threads | Silent truncation would drop comments | WP2: reuse `threads.truncated` and report truncated PRs instead of skipping them silently |
| Default model for `review-learner` | Cost and quality only, and the user can change it | WP3: pick the same default as `sceptic-claude` |

## Work packages

| ID | Outcome | Write scope | Depends on | Completion check |
| --- | --- | --- | --- | --- |
| WP1 | `lesson` note kind exists and validates | `docs/lessons/index.md`, `docs/index.md`, `templates/lesson.md`, `scripts/validate-knowledge.py` (+ its tests), `.agents/skills/cc-learn/SKILL.md` kind table, `docs/kit/rules/knowledge-layout.md` | none | validator tests cover the required lesson fields and an invalid `route`; `./cc validate` passes |
| WP2 | `./cc prs learn` harvests accepted comments deterministically | `scripts/lessons.py`, `scripts/lessons_test.py`, `scripts/prs.py` (subcommand wiring only) | none | unit tests on recorded GraphQL fixtures cover the outdated, resolved-only, VALID-verdict, top-level, bot, truncated and incremental-state cases; no comment body is written to disk (test asserts on `.cc-local/lessons/`) |
| WP3 | `review-learner` agent clusters and matches | `templates/agents/review-learner.json`, `.agents/roles/review-learner/SKILL.md`, `scripts/lessons.py` (agent call + parse), `scripts/validate-control-center.py` if agent ids are listed there | WP1 (lesson fields), WP2 (input format) | parser tests for valid, malformed and single-thread-candidate output; the agent shows up in the `./cc settings` smoke test; `./cc agents sync` is clean |
| WP4 | `cc-lessons` skill drives harvest, confirmation, note writes, count report and gate offer; reviews use lessons | `.agents/skills/cc-lessons/SKILL.md`, `.agents/skills/cc-review/SKILL.md` (knowledge step names `docs/lessons/`), `.agents/skills/cc-help/SKILL.md` | WP1, WP3 | `./cc agents sync` is clean; the skill text states the confirm-before-write and no-project-writes rules |
| WP4b | Council roles see the lessons for the feature's repository, so proposals and writes follow them before push | `scripts/council/run.py` (role prompt), `scripts/council/council_test.py` | WP1 | council test: a role prompt for repo `api` lists an active `api` lesson's summary and path, and leaves out lessons for other repos and superseded ones |
| WP5 | Eval proves a lesson changes review behaviour | `scripts/eval/scenarios.py`, `scripts/eval/fixture.sh`, `scripts/eval/eval_test.py` | WP1, WP4 | the new scenario passes in `./cc eval run`: `cc-review` on a seeded diff that violates a fixture lesson reports `[KNOWLEDGE]` citing `docs/lessons/...`; the grader is unit-tested |
| WP6 | Kit decision 0020 recorded | `docs/kit/decisions/0020-review-lessons.md`, `docs/kit/index.md`, relations in 0012 and 0015 | WP1–WP4 settled | `./cc validate` passes |

Progress: WP1–WP5 and WP4b done on branch `review-lessons` (`./cc check` passes). `./cc eval run review-lessons-lesson --ref eval/review-lessons-wip --scenarios lesson --reps 3`: 3/3 passed (opus, ~$0.26 and ~58 s per run; each run used cc-review, ran `./cc feature ratio verify`, cited the lesson as `[KNOWLEDGE]`, edited nothing). WP6 done: `docs/kit/decisions/0020-review-lessons.md`. Deferred by the user: the comparison against `main` on the existing scenarios. Still open: open question 1 (precision on a real repo). The saved position moves only after the learner succeeds (or with `--harvest-only`), so a failed call loses no comments. Existing CCs get the agent only by copying `templates/agents/review-learner.json` into `catalog/agents/`; the command says so when it is missing. WP2's precision sample (open question 1) and a first real learner run still need a real CC with a catalog repo.

WP1 and WP2 run in parallel (no shared files). WP3 follows both. WP4 and WP5 then run in parallel (disjoint files). WP6 comes last.

## Integration and verification

- `./cc check` on the integration branch: unit tests, the validators, agent config sync and the settings smoke test.
- `./cc eval run review-lessons --scenarios <new>` passes. Comparing against `main` on the existing scenarios shows no regression in pass rate and no more than +5% cost (the extra skill description).
- Manual end-to-end on one real catalog repo: `./cc prs learn <repo>`, hand-check precision on 20 threads (open question 1), confirm one lesson, then see `cc-review` cite it on a PR that violates it.

## Failure, rollback and stop conditions

- **Rollback:** the feature is additive. Reverting the branch removes it. Lesson notes already written in a CC stay valid ordinary notes.
- **Stop and re-plan:** if `isOutdated` precision on the real sample is below 50% even with the commit-touch rule, the accepted-comment signal is wrong.
- **Stop:** if the eval shows existing scenarios regress because of the added skill.
- If `gh` rate limits block a 50-PR backfill, lower the default backfill and say so. Never silently skip PRs.

## Acceptance criteria

1. `./cc prs learn <repo>` lists accepted comments from merged PRs since the last run. It prints per-PR counts and any truncated PRs, and writes nothing but PR numbers and timestamps under `.cc-local/lessons/`.
2. The `review-learner` agent appears in `./cc settings` → Agents. Changing its model there changes the model the next `./cc prs learn` uses.
3. Candidates are anonymized team-level lessons, each with at least two thread permalinks. No login appears in any prompt, note or output.
4. No lesson note is created or updated without an explicit yes. Notes validate under `./cc validate`.
5. Each run reports the repeat-offence count (`matched / accepted`, per lesson).
6. A `route: gate` lesson leads to an offer to start a feature, and nothing is written to the project repo.
7. `cc-review` reports `[KNOWLEDGE]` citing a lesson note when a diff violates it (eval scenario passes).
8. `./cc check` passes. Kit decision 0020 exists and is linked from 0012 and 0015.

## Lifecycle closure

Not closed.

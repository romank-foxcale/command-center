---
id: kit.decision.0020-review-lessons
title: Accepted review comments become user-confirmed, team-level review lessons that reviews and councils apply
status: accepted
summary: ./cc prs learn harvests the review comments accepted on merged catalog PRs (the line changed before merge, or ./cc prs judge found them VALID) without a model call; a read-only review-learner agent, whose model is set in ./cc settings, groups the anonymized comments into candidate lessons and counts the ones that repeat a known lesson; the user confirms each lesson before it is written to docs/lessons/; cc-review cites lessons as [KNOWLEDGE] and council roles see them in their prompts; a checkable lesson is routed to a gate through a normal feature; nothing about a person and no comment text is stored.
verified_at: 2026-10-17
evidence:
  - scripts/lessons.py
  - scripts/lessons_test.py
  - scripts/validate-knowledge.py
  - scripts/validate_knowledge_test.py
  - scripts/council/run.py
  - scripts/council/council_test.py
  - scripts/eval/scenarios.py
  - templates/lesson.md
  - templates/agents/review-learner.json
  - .agents/roles/review-learner/SKILL.md
  - .agents/skills/cc-lessons/SKILL.md
  - .agents/skills/cc-review/SKILL.md
relations:
  - docs/kit/index.md
  - docs/lessons/index.md
  - docs/kit/decisions/0012-review-bar.md
  - docs/kit/decisions/0015-thread-sceptics.md
  - docs/kit/decisions/0007-agent-councils.md
  - docs/kit/decisions/0019-lean-agent-context.md
  - docs/kit/decisions/0022-deterministic-checks-before-review.md
---

# Accepted review comments become user-confirmed, team-level review lessons that reviews and councils apply

## Context

Reviewers keep pointing out the same kinds of shortcomings, and the CC forgot each one as soon as the PR merged. `./cc prs judge` (0015) checks whether a comment holds, and keeps only its verdict. `cc-learn` records a fact only when someone asks. `cc-review` could already cite a note as `[KNOWLEDGE]` (0012), but nothing turned review history into notes. The goal is to stop a mistake reviewers have seen twice from reaching a third PR. This must not profile the people who review, and must not store their conversations.

## Decision

- **Harvest without a model.** `./cc prs learn [repo...]` reads the PRs merged since the last run (the last 50 the first time; `--since` reads from a date without moving the position). A comment is accepted when its inline thread was started by someone other than the PR author and its line changed before merge. A comment `./cc prs judge` judged `VALID` is accepted too, which also covers summaries and top-level comments. Comments from people and from bots both count, tagged only `human` or `bot`.
- **Anonymous, and nothing stored.** People become `PR author` and `Reviewer A, B, ...`, as in 0015. Comment text exists only in memory and on stdout. The learner's provider log goes to a temporary folder that is removed. `.cc-local/lessons/<repo>.json` keeps only the last merge time, the PR number and the harvest time. Lessons are about code and team practice, never about a person.
- **A configurable learner agent.** `review-learner` (`templates/agents/review-learner.json`, read-only, role skill in `.agents/roles/`) is an ordinary catalog agent, so its provider and model are changed in `./cc settings`. It gets each comment under a key such as `api#12/T1`, never a URL, together with its diff hunk and the summaries of current lessons. It returns:
  - matches: a comment and the existing lesson it repeats;
  - candidates: a rule, the repos it covers, a `route`, and at least two supporting comments.
  The runner keeps only entries that cite known keys and lessons and have a valid route. It takes permalinks from the harvest, never from the model. The saved position moves only once the learner has succeeded.
- **Lessons are a note kind.** `docs/lessons/` follows `templates/lesson.md`, which adds `repos`, `occurrences`, `last_seen` and `route` (`note` or `gate`). `./cc validate` checks those fields. `cc-lessons` writes or updates a lesson only after the user's yes on that lesson.
- **Applied before push.** `cc-review` checks every changed hunk against the lessons for the repo and reports a violation as `[KNOWLEDGE]`. Council roles get the repo's lessons in their prompt, ahead of the task.
- **The strongest route wins.** For a lesson a lint or test could enforce (`route: gate`), `cc-lessons` offers to start a normal feature that adds the check: a linter rule or architecture test in the project repo, or a contract check in a workflow when the lesson spans two repos ([0022](0022-deterministic-checks-before-review.md)). Once `./cc verify` enforces it, the lesson's evidence points to the check. The harvest itself never writes to a project repo.
- **Measured.** Each run reports how many accepted comments repeat a known lesson, in total and per lesson. A lesson that keeps matching is not being applied: it is a candidate for a gate. The eval scenario `lesson` proves the wiring: `cc-review`, given a feature that breaks a confirmed lesson, cites the lesson as `[KNOWLEDGE]` and edits nothing. It passed 3 of 3 runs on Opus.

## Options considered

- **Per-reviewer profiles** ("Reviewer X cares about naming"): more tailored, but it is personal data, and it contradicts 0015's rule that claims are judged without knowing who made them. Repo-level conventions carry most of the value.
- **Only VALID verdicts as the signal:** high precision, but it covers only the user's own PRs that were judged, so it yields few lessons.
- **The session agent clusters the comments:** no extra role, but the model can't be configured, and the output would depend on which tool runs the session.
- **A cached store of anonymized comment text:** cheaper to re-cluster, but it relaxes the rule against storing conversations, for little gain.
- **Measuring with `./cc eval` alone:** the eval runs a synthetic fixture and never sees real PRs. It can prove the wiring, not the effect.

## Consequences

- **Cost:** one learner call per harvest run, over all accepted comments of that run. Re-reading with `--since` costs another call.
- **The accepted signal is a proxy.** A force-push or rebase can mark a thread outdated without the comment having caused the change. The two-comment minimum and the user's confirmation limit the noise. Its precision on real repos is not yet measured.
- **Existing CCs:** `review-learner` reaches a new CC through the template. An existing CC copies `templates/agents/review-learner.json` into `catalog/agents/`, and `./cc prs learn` says so when it is missing.
- **Lessons cost context:** every council prompt for a repo grows by one line per lesson. That stays small while lessons stay few and specific.

## Revisit when

- The precision of the accepted signal on a real repo is below about 70%: also require a later commit that touches the commented file.
- The repeat count does not fall for lessons that exist: they are too vague, or should become gates.
- Lessons for one repo grow past a few dozen: summarize or retire them.

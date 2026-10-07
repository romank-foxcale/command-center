---
id: decision.0012-review-bar
title: Reviews report only BREAK, SCOPE and KNOWLEDGE findings, and CLEAN is a verdict
status: accepted
summary: A PR review in a CC reports only evidence-backed [BREAK], [SCOPE] and [KNOWLEDGE] findings, tries to refute each before reporting it, never reports style or nits unless asked, and states a CLEAN verdict with what was checked when nothing clears the bar.
verified_at: 2026-10-07
evidence:
  - .agents/skills/cc-review/SKILL.md
  - scripts/prs.py
  - scripts/prs_test.py
  - scripts/trello.py
relations:
  - docs/index.md
  - docs/decisions/0011-catalog-is-the-repo-scope.md
  - docs/decisions/0009-trello-on-demand.md
---

# Reviews report only BREAK, SCOPE and KNOWLEDGE findings, and CLEAN is a verdict

## Context

Asked to "review", agents read it as "find problems" and pad clean PRs with style remarks and speculative risks. The real findings get lost, and the user cannot tell a clean PR from a review that ran out of ideas.

## Decision

- Three tags only: `[BREAK]` (build, tests or runtime break, with a concrete scenario), `[SCOPE]` (misses or contradicts a quoted acceptance criterion from the PR or its Trello card), `[KNOWLEDGE]` (contradicts a cited CC note).
- Each candidate is searched for hard, then refuted against callers, tests and config; what survives is reported, and what cannot be settled is marked unconfirmed with how to confirm it.
- No findings gives `Verdict: CLEAN`. Every review prints what it checked (build, each criterion, notes read), so a clean verdict can be trusted.
- Nits are not findings; they appear only on request, at most three.
- `./cc prs show` and `./cc trello show --card` supply the PR, its linked cards' descriptions and checklists, so scope is checked against what was asked, not guessed.

## Options considered

- A severity scale (critical to low): every review still fills the low end.
- The generic code-review skill: no access to the CC's cards and notes, and no fixed bar.

## Consequences

- A PR with no acceptance criteria can only be checked against its title and description; the review says so.
- For repos with gates, `./cc prs checkout` puts the PR head into a feature worktree and `./cc feature pr-<repo>-<n> verify` turns `[BREAK]` into a failing gate rather than a judgement. The review branch tracks the fetched PR ref, so a re-run follows new pushes and cleanup does not see unpublished commits. For repos without gates, `[BREAK]` stays a judgement from the code.

## Revisit when

Reviews regularly miss real breaks (lower the bar) or still report noise (tighten the bars per tag).

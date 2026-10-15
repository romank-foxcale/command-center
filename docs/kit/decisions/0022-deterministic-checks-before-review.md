---
id: kit.decision.0022-deterministic-checks-before-review
title: What a tool can decide is a check, so review judges only the rest
status: accepted
summary: Onboarding wires each repo's formatter, linter and architecture rules into its adapter's ordinary checks, a contract between two repos becomes a workflow check that regenerates the consumer's artifact from the producer's spec and fails on drift (ccLib.mkContractCheck, templates/workflow.nix), and cc-review does not re-judge what such a check already enforces.
verified_at: 2026-10-15
evidence:
  - nix/lib/default.nix
  - flake.nix
  - templates/workflow.nix
  - templates/project.nix
  - nix/workflows/default.nix
  - .agents/skills/grill-cc-bootstrap/SKILL.md
  - .agents/skills/cc-review/SKILL.md
  - .agents/skills/cc-lessons/SKILL.md
relations:
  - docs/kit/index.md
  - docs/kit/rules/quality-gates.md
  - docs/kit/rules/project-adapters.md
  - docs/kit/decisions/0008-quality-gates.md
  - docs/kit/decisions/0012-review-bar.md
  - docs/kit/decisions/0020-review-lessons.md
  - docs/kit/decisions/0021-cc-check-in-ci.md
---

# What a tool can decide is a check, so review judges only the rest

## Context

The kit defined test and mutation tools per stack but no formatter, linter or architecture rules, and `nix/workflows/` was empty although the architecture promises executable cross-project contracts. So formatting drift, layering violations and a frontend whose generated API types no longer match the backend's spec were caught, if at all, by the judgment of `cc-review` and councils. That judgment costs a model call, varies between runs, and only sees what is in the diff. A tool decides the same way on every run and costs almost nothing.

## Decision

- **Static checks are ordinary checks.** The adapter runs the stack's formatter, linter and architecture tests in check mode as entries in `checks`, so they run in `./cc check` and every `./cc verify`. Onboarding wires what the repo already configures and proposes the defaults in `docs/kit/rules/quality-gates.md` where it has none. They are not a new quality gate kind: unlike mutation testing they are fast, so nothing justifies keeping them out of the normal checks.
- **Cross-repo contracts are workflow checks.** `ccLib.mkContractCheck` regenerates the consumer's committed artifact from the producer's spec (for example TypeScript types from an `openapi.yaml` with openapi-typescript) and fails with a diff when they differ. `templates/workflow.nix` is the starting point; the template's own `nix/workflows/` stays empty, as 0017 requires of the project layer. The flake check `contract-check` proves the helper passes on a match and fails on drift.
- **Review does not repeat a check.** `cc-review` reports a contract or rule that a check enforces only as the `[BREAK]` of that check failing.
- **Review lessons have a landing place.** A lesson with `route: gate` (0020) becomes a linter rule or architecture test in one repo, or a contract check when it spans repos.

## Options considered

- **A `quality.static` gate kind** next to `quality.mutation`: it would run only under `--quality`, so a formatting or layering break would pass `./cc check`. Rejected because the checks are fast.
- **Leave contracts to review:** each review would re-derive the contract from both repos, and a review that only sees one repo's diff cannot see the drift at all.
- **Comparing specs with an OpenAPI diff tool:** catches breaking spec changes but not a consumer that forgot to regenerate. Regenerate-and-diff covers both, and a CC may add a breaking-change check beside it.

## Consequences

- A producer change fails the contract check until the same feature regenerates the consumer's artifact, so such a change is a feature over both repos. Under `./cc feature <feature> verify` the check sees the feature's worktrees.
- The generator must be deterministic for an unchanged spec; the consumer's formatter runs inside `generate` when its committed file is formatted.
- A repo that does not pass its linter yet starts from a baseline, and the baseline is debt that review no longer sees.

## Revisit when

- Councils still spend findings on what a configured check enforces: feed them the list of checks per repo.
- Most contracts in practice are not generated artifacts (hand-written clients, message schemas): add a second helper for them.

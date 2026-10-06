---
id: decision.0008-quality-gates
title: Language-specific quality gates behind language-neutral skills
status: accepted
summary: Skills say what to prove about tests; each repository's adapter says how, through a named quality.mutation gate that is optional for now and warns when missing.
verified_at: 2026-10-06
evidence:
  - scripts/verify.py
  - scripts/council/run.py
  - nix/lib/default.nix
  - .agents/skills/tdd/SKILL.md
relations:
  - docs/index.md
  - docs/rules/quality-gates.md
  - docs/decisions/0007-agent-councils.md
---

# Language-specific quality gates behind language-neutral skills

## Context

Tests written by the same agent that wrote the code often pass without catching a broken implementation. Mutation testing measures that, but every language has its own tool, and one CC holds repositories in several languages (for example a Java backend and a Python AI service).

## Decision

- The catalog records each repository's `stack`; roles receive it in their context.
- The adapter exposes `quality.mutation` with the tool for its stack; `./cc verify --quality` and councils call it by name and never know the language.
- A missing gate is a warning, so repositories can be onboarded gradually. Councils report "tests were not checked against injected bugs" when it is missing, and "tests pass but miss injected bugs" when it fails.
- Equivalent mutants are marked in code with the tool's skip mechanism and a reason.

## Options considered

- Language-specific skills: duplicates the method per language and drifts.
- A blocking gate from day one: stops every repository that has not been adapted yet.

## Consequences

- Mutation runs are slow, so they stay out of `./cc check`.
- A repository's quality depends on its adapter actually failing on survivors; the rule note lists tool quirks found so far.

## Revisit when

Every repository in a CC has a mutation gate: then make a missing gate blocking for that CC.

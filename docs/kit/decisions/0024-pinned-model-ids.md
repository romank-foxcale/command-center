---
id: kit.decision.0024-pinned-model-ids
title: Agent roles pin full model ids; a floating alias gets a warning
status: accepted
summary: The template's agent roles name full model ids (claude-opus-5-5, not opus), and ./cc check, ./cc validate and ./cc council set-role warn, never fail, when a role in catalog/agents uses an alias that follows the newest model (Claude opus, sonnet, haiku; Cursor auto), so a council's behaviour changes only when the CC changes.
verified_at: 2026-10-17
evidence:
  - scripts/validate-control-center.py
  - scripts/council/run.py
  - scripts/council/providers.py
  - scripts/council/council_test.py
  - templates/agents
relations:
  - docs/kit/index.md
  - docs/kit/decisions/0007-agent-councils.md
  - docs/kit/decisions/0010-live-run-events.md
  - docs/kit/decisions/0022-deterministic-checks-before-review.md
---

# Agent roles pin full model ids; a floating alias gets a warning

## Context

Each role in `catalog/agents/` names a provider and a model. The template shipped Claude roles as `opus`, an alias the Claude CLI resolves to the newest Opus. When a new model ships, every council, sceptic and review learner changes behaviour with no change in the CC, so two runs a week apart are not comparable and a regression has no commit to point at. Run events record the model name a role used ([0010](0010-live-run-events.md)), but an alias records the same name before and after the switch.

## Decision

- The template's roles use full model ids (`claude-opus-5-5`). Codex and Cursor roles already named versioned models.
- `FLOATING_MODELS` in `scripts/validate-control-center.py` lists the aliases that move: Claude `opus`, `sonnet`, `haiku` and Cursor `auto`. `./cc check`, `./cc validate` and `./cc council set-role` (which the settings panel uses) print a warning for a role that uses one.
- It is a warning, not an error: an alias is a valid choice for someone who wants the newest model, and a failing check would push people to edit roles without thinking about it.
- The Claude model picker lists full ids first.

## Options considered

- Fail the check on an alias: forces pinning, but blocks a deliberate choice.
- Resolve the alias at run time and record the resolved id: the Claude CLI does not report it before the call, and it would still not keep runs comparable.
- Leave aliases as the default: the newest model with no upkeep, at the cost of unexplained behaviour changes.

## Consequences

- Moving to a new model is a visible change: `./cc council set-role` or a kit update, with a commit to point at.
- The ids in `CLAUDE_MODELS` (`scripts/council/providers.py`) and the template roles need updating when Anthropic releases models.

## Revisit when

A provider starts reporting the resolved model id for each call, or retires the full ids a CC has pinned.

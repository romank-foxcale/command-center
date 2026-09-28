---
id: decision.0004-plan-lifecycle
title: Plan lifecycle
status: accepted
summary: Every task plan exists in exactly one state: active, archived or completed.
verified_at: 2026-07-21
evidence:
  - scripts/plans.py
  - plans/active/.gitkeep
  - plans/archived/.gitkeep
  - plans/completed/.gitkeep
relations:
  - docs/index.md
  - docs/rules/task-planning.md
---

# Plan lifecycle

## Context

Current, cancelled and finished plans serve different purposes: coordinating work, explaining why something was dropped, and checking the actual result.

## Decision

- `plans/active/` holds current plans.
- `plans/archived/` holds plans that were decided against, with the reason.
- `plans/completed/` holds finished plans with acceptance evidence.

A transition moves the file; it never copies it. The same plan ID in another state is an error. Only an explicitly accepted plan can reach `completed`.

## Consequences

The decision history is preserved, while `active` remains a map of current work only. Long-lived knowledge is still moved into ADRs, the glossary, hacks and debt.

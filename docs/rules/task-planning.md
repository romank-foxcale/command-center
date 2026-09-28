---
id: rules.task-planning
title: Planning tasks for agents
status: active
summary: Grilling turns an unclear task into an evidence-backed plan with non-overlapping work packages and verifiable acceptance.
verified_at: 2026-07-21
evidence:
  - .agents/skills/_shared/grilling-core.md
  - .agents/skills/grill-task-planning/SKILL.md
  - scripts/plans.py
  - templates/task-plan.md
relations:
  - docs/index.md
  - docs/decisions/0004-plan-lifecycle.md
  - docs/rules/knowledge-layout.md
  - docs/rules/worktrees.md
  - docs/glossary/index.md
---

# Planning tasks for agents

## Plan boundary

A task plan holds the goal, scope, unknowns, work graph and acceptance of one task. It does not replace the catalog, the Nix contract or long-lived docs.

A plan is recorded only if it is needed across sessions or agents. A current plan lives in `plans/active/`; after a decision not to carry it out it moves to `plans/archived/`, and after proven completion to `plans/completed/`. Decisions, terms, hacks and debt that will be useful later live separately.

## Lifecycle

- `./cc plan create` creates an active plan from the template.
- `./cc plan accept` records explicit agreement before implementation.
- `./cc plan archive` requires a reason for dropping the plan.
- `./cc plan complete` requires an accepted plan and acceptance evidence.
- Copies of one plan ID in several states are forbidden.

## Agent graph

Every work package has one outcome, an exact write scope, inputs, outputs, dependencies and a completion check. Parallel packages never change the same files or interfaces. Integration and final verification follow the component work.

The plan is ready when an agent without access to the grilling can unambiguously choose the worktree, the change boundaries, the check and the stop condition.

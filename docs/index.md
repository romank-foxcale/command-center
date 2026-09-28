---
id: index
title: Control Center knowledge map
status: active
summary: Minimal entry point into the rules, architecture and decision history.
verified_at: 2026-07-21
evidence:
  - AGENTS.md
relations:
  - docs/architecture/control-center.md
  - docs/rules/bootstrap.md
  - docs/rules/executable-processes.md
  - docs/rules/knowledge-layout.md
  - docs/rules/project-adapters.md
  - docs/rules/task-planning.md
  - docs/rules/worktrees.md
  - docs/decisions/0005-multi-tool-agent-configs.md
---

# Knowledge map

## Mandatory rules

- [Bootstrap and migration](rules/bootstrap.md)
- [Executable processes](rules/executable-processes.md)
- [Markdown knowledge layout](rules/knowledge-layout.md)
- [Connecting sibling projects](rules/project-adapters.md)
- [Planning agent tasks](rules/task-planning.md)
- [Worktree topology](rules/worktrees.md)

## Architecture

- [Control Center boundaries](architecture/control-center.md)

## Decisions

- [Nix as the format for executable knowledge](decisions/0001-nix-executable-knowledge.md)
- [Atomic linked notes](decisions/0002-atomic-linked-notes.md)
- [Template as a temporary seed](decisions/0003-template-as-seed.md)
- [Plan lifecycle](decisions/0004-plan-lifecycle.md)
- [One set of skills for every AI tool](decisions/0005-multi-tool-agent-configs.md)

## Current context

- [Technical debt](debt/index.md)
- [Hacks](hacks/index.md)
- [Projects](projects/index.md)
- [Glossary](glossary/index.md)

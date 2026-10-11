---
id: index
title: Control Center knowledge map
status: active
summary: Minimal entry point into the rules, architecture and decision history.
verified_at: 2026-10-11
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
  - docs/decisions/0006-target-platform-gates.md
  - docs/decisions/0007-agent-councils.md
  - docs/decisions/0008-quality-gates.md
  - docs/decisions/0009-trello-on-demand.md
  - docs/decisions/0010-live-run-events.md
  - docs/decisions/0011-catalog-is-the-repo-scope.md
  - docs/decisions/0012-review-bar.md
  - docs/decisions/0013-rule-hooks.md
  - docs/decisions/0014-cursor-provider-and-security-council.md
  - docs/decisions/0015-thread-sceptics.md
  - docs/decisions/0016-per-cc-repos-and-worktrees.md
  - docs/decisions/0017-runtime-flows.md
  - docs/rules/quality-gates.md
  - docs/flows/index.md
---

# Knowledge map

## Mandatory rules

- [Bootstrap and migration](rules/bootstrap.md)
- [Executable processes](rules/executable-processes.md)
- [Markdown knowledge layout](rules/knowledge-layout.md)
- [Connecting sibling projects](rules/project-adapters.md)
- [Planning agent tasks](rules/task-planning.md)
- [Quality gates per stack](rules/quality-gates.md)
- [Worktree topology](rules/worktrees.md)

## Architecture

- [Control Center boundaries](architecture/control-center.md)

## Decisions

- [Nix as the format for executable knowledge](decisions/0001-nix-executable-knowledge.md)
- [Atomic linked notes](decisions/0002-atomic-linked-notes.md)
- [Template as a temporary seed](decisions/0003-template-as-seed.md)
- [Plan lifecycle](decisions/0004-plan-lifecycle.md)
- [One set of skills for every AI tool](decisions/0005-multi-tool-agent-configs.md)
- [Every target platform has its own gate](decisions/0006-target-platform-gates.md)
- [Agent roles and councils bound to models](decisions/0007-agent-councils.md)
- [Language-specific quality gates behind language-neutral skills](decisions/0008-quality-gates.md)
- [Trello cards are updated on demand](decisions/0009-trello-on-demand.md)
- [Long runs report progress as a live event stream](decisions/0010-live-run-events.md)
- [The catalog is the CC's repo scope](decisions/0011-catalog-is-the-repo-scope.md)
- [Reviews report only BREAK, SCOPE and KNOWLEDGE findings](decisions/0012-review-bar.md)
- [Claude Code hooks enforce the hard rules early; the gates still decide](decisions/0013-rule-hooks.md)
- [Cursor is a read-only provider, and security review is a three-model council](decisions/0014-cursor-provider-and-security-council.md)
- [Review conversations are judged by two anonymous sceptics, and a judge settles only their splits](decisions/0015-thread-sceptics.md)
- [Every CC keeps its own repos and worktrees inside its folder](decisions/0016-per-cc-repos-and-worktrees.md)
- [Runtime flows are notes whose steps cite project code](decisions/0017-runtime-flows.md)

## Current context

- [Runtime flows](flows/index.md): how each project runs, step by step, with cited code
- [Technical debt](debt/index.md)
- [Hacks](hacks/index.md)
- [Projects](projects/index.md)
- [Glossary](glossary/index.md)

---
id: decision.0003-template-as-seed
title: Template as a temporary seed
status: accepted
summary: The cc_template clone stays a read-only source, and the final CC is created as a separate Git repository in the parent folder.
verified_at: 2026-07-21
evidence:
  - BOOTSTRAP.md
  - scripts/materialize-template.py
relations:
  - docs/index.md
  - docs/rules/bootstrap.md
  - docs/rules/worktrees.md
---

# Template as a temporary seed

## Context

The user starts an AI tool from the folder of the future CC. It may be empty, or it may already contain a CC of another format. A nested Git clone must not determine the lifecycle of the final project.

## Decision

Treat `cc_template/` as a read-only seed. In `new` mode, copy its tracked files into the parent without overwriting. In `migration` mode, adapt it after a read-only inventory. After acceptance, the user deletes the seed.

`cc-kit new` performs the same materialization directly from the installed kit, without a nested clone.

## Consequences

- The target CC has its own Git history.
- Template changes do not silently leak into a specific CC.
- A session started with a nested `cc_template/` must point explicitly to `cc_template/BOOTSTRAP.md`, because AI tools do not look for project skills inside a child Git repository.

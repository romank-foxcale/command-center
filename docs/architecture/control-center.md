---
id: architecture.control-center
title: Control Center boundaries
status: active
summary: The Control Center holds the map, executable cross-project contracts and context, but never copies the sibling repositories.
verified_at: 2026-07-21
evidence:
  - templates/control-center.json
  - flake.nix
  - nix/lib/default.nix
relations:
  - docs/index.md
  - docs/rules/bootstrap.md
  - docs/rules/executable-processes.md
  - docs/rules/project-adapters.md
  - docs/rules/worktrees.md
---

# Control Center boundaries

## Inside

- flake inputs and project adapters;
- a machine-readable catalog of repositories, workflows and benchmarks;
- cross-project derivation graphs and checks;
- apps for external and privileged operations;
- knowledge rules and a log of cross-project decisions;
- links to runtime sources of truth.

## Outside

- the source code of sibling projects;
- secrets;
- the actual state of production;
- full copies of project documentation;
- a general-purpose UI.

Base clones and feature worktrees are also outside: `../repos/` and `../worktrees/<feature>/`.

## Flow

```text
sibling sources → project adapters → packages/checks
                                      ↓
                              cross-project workflow
                                      ↓
                           artifact → runtime app → verify
```

Markdown explains the boundaries and reasons. The Nix graph proves the process still works.

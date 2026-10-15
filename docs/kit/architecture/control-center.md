---
id: kit.architecture.control-center
title: Control Center boundaries
status: active
summary: The Control Center holds the map, executable cross-project contracts and context, but never keeps the source of its catalog repositories in its own Git.
verified_at: 2026-10-15
evidence:
  - templates/control-center.json
  - flake.nix
  - nix/lib/default.nix
  - .gitignore
relations:
  - docs/index.md
  - docs/kit/rules/bootstrap.md
  - docs/kit/rules/executable-processes.md
  - docs/kit/rules/project-adapters.md
  - docs/kit/rules/worktrees.md
  - docs/kit/decisions/0016-per-cc-repos-and-worktrees.md
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

- the source code of the catalog projects;
- secrets;
- the actual state of production;
- full copies of project documentation;
- a general-purpose UI.

Base clones and feature worktrees live inside the CC folder but outside Git: `repos/` and `worktrees/<feature>/` are git-ignored ([0016](../decisions/0016-per-cc-repos-and-worktrees.md)).

## Flow

```text
project sources → project adapters → packages/checks
                                      ↓
                              cross-project workflow
                                      ↓
                           artifact → runtime app → verify
```

Markdown explains the boundaries and reasons. The Nix graph proves the process still works.

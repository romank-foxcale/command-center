---
id: rules.executable-processes
title: Executable processes
status: active
summary: All knowledge about building, testing, packaging and running is expressed as Nix outputs.
verified_at: 2026-10-09
evidence:
  - flake.nix
  - nix/lib/default.nix
  - nix/workflows/default.nix
  - templates/project.nix
relations:
  - docs/architecture/control-center.md
  - docs/rules/project-adapters.md
  - docs/decisions/0001-nix-executable-knowledge.md
---

# Executable processes

## Contract

| Knowledge | Flake output | Property |
|---|---|---|
| Buildable artifact | `packages` | Pure, cacheable, reproducible |
| Automatic verification | `checks` | Runs through `nix flake check` |
| Run/deploy/E2E | `apps` | Explicit runtime side effect |
| Developer environment | `devShells` | Tool versions are defined in code |
| Host/service | `nixosModules` | Declarative state and rollback |

## Invariants

- A cross-project workflow consumes derivation outputs; it never looks for artifacts at arbitrary paths.
- Changing a source input invalidates the dependent builds and checks.
- A command found during diagnosis does not count as knowledge until it is expressed in Nix.
- Networked, interactive and privileged actions are never disguised as pure checks.
- Markdown may explain the goal and the trade-off, but it is not a build runbook.

## Example

A cross-project end-to-end test is a chain of outputs, not a script that finds its inputs on disk:

```text
project A package ─┐
                   ├→ dockerTools image → HTTP service → E2E app
project B package ─┘
```

Each project's adapter (`nix/projects/`) builds its package as a check. The workflow (`nix/workflows/`, `ccLib.mkWorkflow`) builds the image from those packages, which is also a check. Running Docker stays an app, because it needs an external daemon.

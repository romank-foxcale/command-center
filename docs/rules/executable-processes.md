---
id: rules.executable-processes
title: Executable processes
status: active
summary: All knowledge about building, testing, packaging and running is expressed as Nix outputs.
verified_at: 2026-07-20
evidence:
  - flake.nix
  - nix/lib/default.nix
  - examples/cpp-docker-e2e/workflow.nix
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

`examples/cpp-docker-e2e/` expresses this chain:

```text
cpp-a derivation ─┐
                  ├→ dockerTools image → HTTP service → E2E app
cpp-b derivation ─┘
```

Building the C++ programs and the image is part of the checks. Running Docker stays an app, because it needs an external daemon.

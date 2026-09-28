---
id: decision.0001-nix-executable-knowledge
title: Nix as the format for executable knowledge
status: accepted
summary: Processes are described as Nix flakes; NixOS is used for machines and services, not as a universal format for everything.
verified_at: 2026-07-20
evidence:
  - flake.nix
  - nix/lib/default.nix
relations:
  - docs/rules/executable-processes.md
  - docs/architecture/control-center.md
---

# Nix as the format for executable knowledge

## Context

Markdown commands go stale without anyone noticing. A cross-project build must break as soon as an incompatible change lands.

## Decision

Use flake outputs as the public interface of processes:

- derivations/packages: builds;
- checks: automatic verification;
- apps: side effects and runtime;
- NixOS modules/tests: hosts and long-running services.

## Consequences

- The dependency graph becomes computable and cacheable.
- Sources must be pinned.
- Nix becomes a mandatory prerequisite.
- Docker E2E on macOS needs a Linux builder/CI or a separate runtime adapter.

## Revisit when

If Nix cannot express a significant part of the real processes without a large impure layer, compare Bazel, Earthly and a CI-native workflow on a single pipeline.

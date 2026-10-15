---
id: kit.decision.0006-target-platform-gates
title: Every target platform has its own gate
status: accepted
summary: Each catalog project repository declares the platforms it ships on, and is verified only when the gate of every declared platform passes, including a real Windows host gate.
verified_at: 2026-10-15
evidence:
  - scripts/repositories.py
  - scripts/validate-control-center.py
  - scripts/verify.py
  - nix/lib/default.nix
  - flake.nix
  - .agents/skills/grill-cc-bootstrap/SKILL.md
relations:
  - docs/index.md
  - docs/kit/rules/project-adapters.md
  - docs/kit/decisions/0001-nix-executable-knowledge.md
  - docs/kit/decisions/0011-catalog-is-the-repo-scope.md
---

# Every target platform has its own gate

## Context

Nix builds and tests only on Linux and macOS. A Windows-only application was pushed after its checks passed on Linux and then failed on Windows: nothing recorded that the product ships on Windows, so nothing required a Windows check.

## Decision

- Each project repository descriptor has a required `targets` list (`windows`, `linux`, `macos`), asked from the user at onboarding and changed with `./cc repo set-targets`. A read-only reference repository has none and is never verified ([0011](0011-catalog-is-the-repo-scope.md)).
- The adapter declares one gate per target in `ccLib.mkProject { targets.<platform> = ...; }`: a derivation (pure check, run by `./cc check`) or an app (a real host, run by `./cc verify`).
- `ccLib.mkWindowsHostGate` runs a PowerShell script with the real toolchain on the Windows host from WSL, in a temporary Windows copy of the sources.
- The bootstrap check fails when an adapted or verified repository has a target without a gate. `./cc verify` runs every flake check and every target gate; only then may a repository be `verified`. Changing the targets of a verified repository resets it to `adapted`.

## Options considered

- Cross-compiling with MinGW and testing under Wine: pure and reproducible, but not the real toolchain or OS; allowed only as an extra early gate.
- A Windows CI runner only: authoritative but too late, after the push; complements the host gate.

## Consequences

- A windows gate needs WSL on a Windows host; on other machines `./cc verify` reports it as failed rather than skipping it.
- Gate scripts are impure: they use the host toolchain, which the CC does not pin.

## Revisit when

Nix can build and test natively for Windows, or the CC gains a remote Windows runner adapter.

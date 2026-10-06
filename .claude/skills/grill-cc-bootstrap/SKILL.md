---
name: grill-cc-bootstrap
description: Conduct an evidence-first grilling session that creates a new Control Center from a temporary cc_template clone or migrates an existing CC of another format. Use when the user asks to bootstrap, configure, adapt, onboard, or migrate a Control Center and its repositories, workflows, benchmarks, executable Nix contracts, and durable knowledge.
---

# Grill CC bootstrap

First read `../_shared/grilling-core.md` in full, then `BOOTSTRAP.md`. Apply both contracts together.

## New CC

1. Determine `template_root` and `target_root` as described in `BOOTSTRAP.md`. If the CC was created with `cc-kit new`, steps 1–2 are already done.
2. Run the materialization; continue from `target_root`.
3. Record the name, status and topology in `control-center.json`.
4. Collect the use cases, boundaries and permissions.
5. Build the repository inventory. Do not write adapters until names, roles and relationships are agreed.
6. Onboard one repo at a time: `./cc repo add --targets ...` → inspect → flake input/adapter → package/check and one gate per target → `./cc verify <id>` → `./cc repo set-status <id> verified`.
7. Only then assemble workflows and benchmarks.
8. Replace the template README and project map with real data; remove the examples and placeholders. Keep `GUIDE.md`, `install/`, `CLAUDE.md` and `.claude/skills`: they are the entry point for people and AI tools.

## Migration

1. Do not change any files before a read-only inventory.
2. Find projects, workflows, build/test/deploy, knowledge, secrets boundaries and runtime integrations.
3. Map each entity to `catalog`, `nix/projects`, `nix/workflows`, `benchmarks`, `docs` or `external`.
4. Mark each one `preserve`, `transform`, `replace` or `drop`; a `drop` requires a reason and agreement.
5. Migrate one vertical slice at a time. Treat the legacy setup as the oracle until equivalence is proven.
6. Do not copy Markdown commands: rebuild the executable contract from them and from the actual CI.
7. Do not delete the legacy setup before the slice is verified.

## Repository grilling

First study the repo and its CI, then close the gaps: remote/branch/role/owner; inputs/outputs/consumers; build/test interface; system/network dependencies; platforms/hardware; secrets/datasets/models/external state; the minimal adapter check.

Put build commands straight into the Nix adapter, not into the grilling transcript.

### Target platforms

Always ask, never infer: "Which platforms does `<repo>` ship on: windows, linux, macos?" CI or a Dockerfile shows where something is built, not where it runs. Record the answer with `--targets` on `./cc repo add`. For each target, agree on its gate:

- a pure Nix check (`targets.<platform> = <derivation>`) when Nix can build and test natively for that platform;
- `ccLib.mkWindowsHostGate` for windows: a PowerShell script that builds and tests with the real toolchain on the Windows host from WSL. Ask for the toolchain and the exact build and test commands;
- a cross-compiled or emulated check (MinGW, Wine) only as an extra early signal, never as the only windows gate.

A target the user names but nobody can gate yet stays in `targets`; mark the repo `blocked` with that reason instead of dropping the target.

## Acceptance

- `control-center.json` and the catalog are valid.
- Every repo declares its targets and is verified on all of them by `./cc verify`, or has an explicit blocker.
- Cross-repo relationships are represented by a workflow/check.
- The critical path passes end to end.
- The target CC does not depend on `cc_template`.

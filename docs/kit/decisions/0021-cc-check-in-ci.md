---
id: kit.decision.0021-cc-check-in-ci
title: CI runs ./cc check on every pull request to the CC
status: accepted
summary: A GitHub Actions workflow shipped with the template runs the same ./cc check a developer runs, with Nix installed by a pinned action, a read-only token and no secrets, so the gates that back the hooks run even when nobody runs them by hand; every CC materialized from the template gets it as a tracked file.
verified_at: 2026-10-15
evidence:
  - .github/workflows/cc-check.yml
  - cc
  - flake.nix
  - scripts/materialize-template.py
relations:
  - docs/kit/index.md
  - docs/kit/decisions/0001-nix-executable-knowledge.md
  - docs/kit/decisions/0003-template-as-seed.md
  - docs/kit/decisions/0013-rule-hooks.md
---

# CI runs ./cc check on every pull request to the CC

## Context

The hooks catch rule breaks only in Claude Code, and only in the shell text they see; [0013](0013-rule-hooks.md) relies on `./cc check` and `./cc verify` to catch the rest. Nothing ran those gates unless a person or an agent remembered to, so a change made with another tool, or with a hook bypassed, could merge unchecked. A deterministic gate does this job; it needs no agent, only a runner.

## Decision

- `.github/workflows/cc-check.yml` runs `./cc check` on every pull request and on pushes to `main`: the same entry point a developer runs, so CI and local runs cannot drift apart.
- Nix comes from `cachix/install-nix-action`, and every action is pinned by commit SHA with its version in a comment.
- The job gets `contents: read` and no secrets.
- The template tracks the workflow, so `materialize-template.py` (and `cc-kit new`) copies it into every new CC without special handling.
- CI runs `./cc check`, not `./cc verify`: verify also needs clones of the catalog repos, their target platform gates and the branch history of feature worktrees, which a CC's own runner does not have.

## Options considered

- No CI, gates by discipline: the gap this note closes.
- A workflow that calls `nix flake check` directly: it would skip the lock refresh in `./cc` and become a second definition of the gate.
- `DeterminateSystems/nix-installer-action`: equivalent here; the choice is not load-bearing.

## Consequences

- A CC whose flake inputs are private repositories fails in CI until it grants the job read access to them; that token is that CC's own decision, never the template default.
- A CC migrated from another format gets the workflow only through the migration, not by materialization.
- A CC hosted outside GitHub ports the three steps to its CI; the gate itself stays `./cc check`.
- Making the check required before merge is a branch protection setting of each CC's repository, outside the kit.

## Revisit when

`./cc verify` can run in CI without the catalog clones, or a CC needs a runner other than GitHub Actions often enough to ship a second workflow.

---
id: rules.bootstrap
title: Control Center bootstrap and migration
status: active
summary: The template is cloned as a nested read-only seed (or installed as the kit), and the target CC is created in the parent folder through evidence-first grilling.
verified_at: 2026-07-21
evidence:
  - BOOTSTRAP.md
  - scripts/materialize-template.py
  - .agents/skills/grill-cc-bootstrap/SKILL.md
relations:
  - docs/index.md
  - docs/architecture/control-center.md
  - docs/decisions/0003-template-as-seed.md
  - docs/rules/project-adapters.md
  - docs/rules/worktrees.md
---

# Control Center bootstrap and migration

## Boundary

`cc_template/` is a temporary source of the protocol and files. It never becomes a submodule or a folder of the final CC. Materialization copies only files tracked by Git and never overwrites a non-empty target.

## Modes

- `new`: safe materialization, then grilling and one-by-one repository onboarding.
- `migration`: read-only inventory, mapping onto the target model, and a vertical-slice migration compared against the legacy behavior.

Migration never justifies losing meaning. An entity is either preserved, or its replacement or removal is recorded as a decision.

## State

`control-center.json` holds the schema version, name, bootstrap status and topology. `catalog/` holds one descriptor per repository, workflow and benchmark. The conversation and internal reasoning are not stored.

`ready` means the descriptors agree with the Nix contracts and the critical workflow is verified. Only then is `cc_template/` no longer needed.

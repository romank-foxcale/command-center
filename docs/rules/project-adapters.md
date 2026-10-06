---
id: rules.project-adapters
title: Connecting sibling projects
status: active
summary: Every external repository is connected through a catalog descriptor, a pinned source and a Nix adapter with packages, checks and apps.
verified_at: 2026-07-21
evidence:
  - scripts/repositories.py
  - nix/projects/default.nix
  - templates/project.nix
  - examples/cpp-docker-e2e/projects.nix
  - nix/lib/default.nix
relations:
  - docs/architecture/control-center.md
  - docs/rules/executable-processes.md
  - docs/projects/index.md
  - docs/decisions/0006-target-platform-gates.md
  - docs/rules/quality-gates.md
---

# Connecting sibling projects

## Project contract

`catalog/repositories/<id>.json` records the remote, default branch, role, target platforms, stack (languages), flake input, adapter and onboarding status. The descriptor is created by `./cc repo add`; build commands never go into it.

The adapter is created with `ccLib.mkProject` and declares:

- `src`: a pinned flake input or a local source override;
- `packages`: the project's artifacts;
- `checks`: builds and tests;
- `apps`: running, generation, external integrations;
- `targets`: one gate per catalog target platform, a check or a host app (see [target gates](../decisions/0006-target-platform-gates.md));
- `quality`: optional `quality.mutation` gate with the mutation tool for the repository's stack (see [quality gates](quality-gates.md));
- `metadata`: role and owner.

The adapter's attribute name in `nix/projects` equals the catalog id, so its targets can be matched against the catalog.

The remote source is pinned in `flake.lock`. Local development does not change the contract: the same input is temporarily overridden to `path:../repo`.

## Division of responsibility

A project adapter knows how to produce the verifiable outputs of one repository. A workflow knows how to connect the outputs of several projects. Project build logic is never duplicated in a workflow.

## Drift

If upstream changes its structure, dependencies or test interface, the adapter/check breaks. The fix goes there; it is never masked by updating Markdown.

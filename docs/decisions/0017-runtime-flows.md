---
id: decision.0017-runtime-flows
title: Runtime flows are notes whose steps cite project code, checked against the pinned or feature source
status: accepted
summary: How a project runs (startup, a request's lifecycle, jobs, and later flows across repos) is kept as flow notes in docs/flows whose evidence cites project code as repo:<id>/<path>#<symbol>; the knowledge check fails when cited code is gone from the adapter source or a feature's worktree, cc-review checks every flow whose cited code a PR edits, and councils receive the flows of their repository.
verified_at: 2026-10-11
evidence:
  - scripts/validate-knowledge.py
  - scripts/validate_knowledge_test.py
  - flake.nix
  - templates/flow.md
relations:
  - docs/flows/index.md
  - docs/glossary/runtime-flow.md
  - docs/rules/knowledge-layout.md
  - docs/decisions/0002-atomic-linked-notes.md
  - docs/decisions/0007-agent-councils.md
  - docs/decisions/0012-review-bar.md
---

# Runtime flows are notes whose steps cite project code

## Context

Agents read code well but not how it runs: the order of startup, which handler runs a request, what a background job triggers, where config comes from and, once repos interact, which repo calls or consumes which. Reconstructing that costs tokens on every task, and inside a council a role sees only one worktree. A written map helps only while it is true; a stale one misleads more than none, and the CC never fixes drift by editing a description.

## Decision

- A runtime flow is one note in `docs/flows/`, from `templates/flow.md`: its purpose, a Mermaid sequence diagram and numbered steps. It records order and reasons, never restated code or commands.
- Evidence may cite project code as `repo:<id>/<path>#<symbol>`: `<id>` is a catalog repository of kind `project` with an adapter, `<path>` is relative to its root, and the optional `<symbol>` is text that must appear in the file. Line numbers are never used. A citation in a note's text must also be listed in its evidence.
- The knowledge check resolves `<id>` to the adapter's `src`, which `./cc feature <f> verify` replaces with the feature's worktree; outside Nix it uses `repos/project/<id>`. It fails when the repository is unknown, a reference repository or without an adapter, or when the cited file or symbol is missing. So a feature that removes cited code fails its own verify.
- An edit to a cited file that keeps the file and symbol is not a check failure: `cc-review` reads every flow citing a changed file, reports a `[KNOWLEDGE]` finding naming the step when the change makes it untrue, with re-verifying the flow as the fix, and otherwise lists the flow as still holding ([0012](0012-review-bar.md)).
- The council runner gives every role the active flows that cite its repository ([0007](0007-agent-councils.md)). The `cc-flow` skill drafts and re-verifies flows, and the user confirms every flow before it is written.

## Options considered

- Hash every cited file and fail on any change: catches semantic drift, but every unrelated edit in a large file blocks verify.
- Warnings only: never blocks, so stale flows survive unnoticed.
- Flows generated from static analysis or runtime traces: no hand-written drift, but heavy per stack and blind to intent; possible later as evidence for a flow, not a replacement.

## Consequences

- A repository must be onboarded with an adapter before its code can be cited.
- A symbol matched as plain text can survive in a comment after the code is gone.
- Every council call pays the tokens of its repository's flows.

## Revisit when

Two catalog repositories interact at runtime and their contracts need a check of their own, a cross-repo smoke test can prove a flow, or flows per repository grow past about five.

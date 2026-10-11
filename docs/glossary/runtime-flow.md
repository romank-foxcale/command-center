---
id: glossary.runtime-flow
title: Runtime flow
status: active
summary: The order in which a project's code runs for one trigger (startup, a request, a job, a message), written as a flow note in docs/flows whose steps cite the code.
verified_at: 2026-10-11
evidence:
  - templates/flow.md
relations:
  - docs/glossary/index.md
  - docs/decisions/0017-runtime-flows.md
  - docs/flows/index.md
---

# Runtime flow

## Definition

What happens, in order, when one trigger runs in a catalog project: startup, an incoming request, a scheduled job, a consumed message. It may stay inside one repository or cross several. It is written as a note in `docs/flows/` whose steps cite the code that performs them.

## Not to be confused with

- A workflow in `nix/workflows`: how the build outputs of several projects are combined and checked. A workflow is executed by Nix; a runtime flow describes the running application.
- A plan: the work to change something. A flow describes how the code runs now.
- A call graph: every call. A flow keeps only the steps a change needs to know about.

## Scope

Catalog repositories of kind `project` with an adapter. Reference repositories are never the source of a flow.

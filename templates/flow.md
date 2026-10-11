---
id: flows.flow-name
title: Flow name
status: active
summary: What triggers this flow, what it ends with, and which repositories it runs through.
verified_at: 2026-10-11
evidence:
  - repo:repo-id/path/to/entry.ext#entry_symbol
relations:
  - docs/flows/index.md
---

# Flow name

## Purpose

When this flow runs, and what a change to it must keep working.

## Sequence

```mermaid
sequenceDiagram
    participant Caller
    participant App as repo-id
    Caller->>App: trigger
    App->>App: main step
    App-->>Caller: result
```

## Steps

1. **What happens first.** Why here and in this order. `repo:repo-id/path/to/entry.ext#entry_symbol`
2. **What happens next.** Cite every step's code, and list each citation in `evidence`.

## Contracts

Only when the flow crosses repositories: the API, message, file or table each side relies on, and which repository owns it.

## Limits

What this flow leaves out, such as error paths or configuration it does not cover.

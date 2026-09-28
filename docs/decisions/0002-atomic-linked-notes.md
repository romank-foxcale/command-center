---
id: decision.0002-atomic-linked-notes
title: Atomic linked notes
status: accepted
summary: Explanatory knowledge is stored as small Markdown nodes with evidence and explicit relations.
verified_at: 2026-07-20
evidence:
  - scripts/validate-knowledge.py
  - templates/note.md
relations:
  - docs/rules/knowledge-layout.md
---

# Atomic linked notes

## Context

Monolithic documentation uses up the model's context and goes stale quickly. Full-text search does not explain which pieces of knowledge are causally related.

## Decision

Use Obsidian-compatible Markdown with mandatory metadata, evidence and relations. Indexes serve as a map, not an encyclopedia.

## Consequences

- The agent loads only the local subgraph.
- Relations and freshness can be validated.
- Writing a note takes more discipline.
- A derived graph can be added later without changing the source of truth.

---
id: rules.knowledge-layout
title: Markdown knowledge layout
status: active
summary: Markdown holds atomic facts, reasons, constraints, decisions, hacks and debt in a linked graph.
verified_at: 2026-10-11
evidence:
  - scripts/validate-knowledge.py
  - templates/note.md
relations:
  - docs/index.md
  - docs/decisions/0002-atomic-linked-notes.md
  - docs/decisions/0017-runtime-flows.md
---

# Markdown knowledge layout

## What to record

- architectural boundaries and invariants;
- the reasons for decisions and the options considered;
- non-obvious hacks and the conditions for removing them;
- technical debt and its impact;
- verified facts that cannot be quickly derived from the code;
- runtime flows: the order in which a project runs for one trigger, in `docs/flows/` ([0017](../decisions/0017-runtime-flows.md)).

## What not to record

- build and test commands;
- secrets and personal data;
- full conversations and chain-of-thought;
- restatements of code that add no meaning;
- unconfirmed hypotheses presented as facts.

## Node format

Every note uses `templates/note.md`: a stable `id`, a short `summary`, a status, a verification date, evidence and typed context through relations.

Paths in `evidence` and `relations` are given from the repository root. Evidence may also cite a catalog project's code as `repo:<id>/<path>#<symbol>`; the knowledge check fails when the cited file or symbol is gone. The body uses ordinary relative Markdown links: they work in GitHub and Obsidian.

## Size and navigation

- one file, one piece of knowledge;
- aim for at most 220 lines;
- an index leads to a domain; it does not list every detail;
- the agent follows direct relations and does not load the whole vault;
- archived and superseded notes are not read without a reason.

A large primary summary can be kept with `kind: research-reference`. It is not canonical knowledge, is not loaded automatically, and may exceed the limit; durable conclusions from it are moved into ordinary atomic notes.

`./cc validate` checks frontmatter, ID uniqueness, evidence, relations and Markdown links.

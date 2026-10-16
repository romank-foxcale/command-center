---
id: kit.rules.knowledge-layout
title: Markdown knowledge layout
status: active
summary: Markdown holds atomic facts, reasons, constraints, decisions, hacks and debt in a linked graph.
verified_at: 2026-10-15
evidence:
  - scripts/validate-knowledge.py
  - templates/note.md
  - templates/lesson.md
  - cc
relations:
  - docs/index.md
  - docs/kit/decisions/0002-atomic-linked-notes.md
---

# Markdown knowledge layout

## What to record

- architectural boundaries and invariants;
- the reasons for decisions and the options considered;
- non-obvious hacks and the conditions for removing them;
- technical debt and its impact;
- verified facts that cannot be quickly derived from the code.

## Two layers

- `docs/kit/` is the kit's knowledge: rules, architecture and kit decisions with `kit.` ids. It is identical in every CC, replaced as a whole on a kit update, and never edited in a CC.
- The rest of `docs/` and `plans/` is this CC's own knowledge: its decisions (numbered from 0001), debt, hacks, projects, review lessons and glossary. A decision that changes kit behaviour for this CC names the kit decision it overrides ([0017](../decisions/0017-kit-and-project-layers.md)).

## What not to record

- build and test commands;
- secrets and personal data;
- full conversations and chain-of-thought;
- restatements of code that add no meaning;
- unconfirmed hypotheses presented as facts.

## Node format

Every note uses `templates/note.md`: a stable `id`, a short `summary`, a status, a verification date, evidence and typed context through relations.

Paths in `evidence` and `relations` are given from the repository root. The body uses ordinary relative Markdown links: they work in GitHub and Obsidian.

## Size and navigation

- one file, one piece of knowledge;
- aim for at most 220 lines;
- an index leads to a domain; it does not list every detail;
- the agent follows direct relations and does not load the whole vault;
- archived and superseded notes are not read without a reason.

A large primary summary can be kept with `kind: research-reference`. It is not canonical knowledge, is not loaded automatically, and may exceed the limit; durable conclusions from it are moved into ordinary atomic notes.

A review lesson in `docs/lessons/` uses `templates/lesson.md`, which adds `repos`, `occurrences`, `last_seen` and `route` (`note` or `gate`).

`./cc validate` checks frontmatter, ID uniqueness, evidence, relations, Markdown links and the lesson fields.

`./cc validate` and `./cc check` also warn, without failing, when an evidence file tracked in this repository was committed after the note's `verified_at` ([0023](../decisions/0023-stale-evidence-warning.md)); a CC skips `docs/kit/`, which only the template can fix. Re-check the note against the change, then refresh `verified_at` or correct the note; never bump the date without looking.

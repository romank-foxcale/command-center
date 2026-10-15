---
id: kit.decision.0017-kit-and-project-layers
title: Kit knowledge and a CC's own knowledge are separate layers
status: accepted
summary: The kit's rules, architecture and decisions live in docs/kit with kit. ids, identical in every CC and replaced as a whole on a kit update; a CC's own decisions, debt, hacks, projects, glossary and plans live in the rest of docs/ and plans/, ship empty in the template and are committed only to that CC; a CC overrides kit behaviour with its own decision, never by editing docs/kit, and a hook asks before such an edit.
verified_at: 2026-10-15
evidence:
  - docs/kit/index.md
  - docs/decisions/index.md
  - scripts/rule_hooks.py
  - scripts/rule_hooks_test.py
  - scripts/validate-knowledge.py
  - scripts/validate_knowledge_test.py
relations:
  - docs/kit/index.md
  - docs/kit/decisions/0003-template-as-seed.md
  - docs/kit/decisions/0013-rule-hooks.md
  - docs/kit/rules/knowledge-layout.md
---

# Kit knowledge and a CC's own knowledge are separate layers

## Context

The template was used to build CCs, and its notes mixed two kinds of knowledge: why every CC works the way it does, and facts and plans of the CCs it was built with. Both shared `docs/decisions/` and one numbering. A new CC started with someone else's history, and bringing a kit improvement into a CC meant renumbering and merging notes by hand.

## Decision

- **Kit layer:** `docs/kit/` holds the rules, the architecture and the kit decisions, with `kit.` ids. The template owns it; every CC carries an identical copy; a kit update replaces it as a whole.
- **Project layer:** `docs/decisions/`, `docs/debt/`, `docs/hacks/`, `docs/projects/`, `docs/glossary/`, `docs/lessons/` and `plans/` belong to the CC. The template ships them as empty indexes. A CC's decisions are numbered from 0001 and committed only to that CC's repository. In the template, `./cc validate` fails when any of these folders tracks more than its index or `.gitkeep`. A working plan for a kit change stays untracked there.
- **Overrides:** to change kit behaviour for one CC, the CC records its own decision that names the kit decision it overrides. It never edits `docs/kit/`.
- **Protection:** in a CC (a folder with `control-center.json`), the Claude Code hook asks before an edit under `docs/kit/` ([0013](0013-rule-hooks.md)). The template repository edits the kit freely.
- The template carries no decision, plan or data of the people who use it.

## Options considered

- One folder, with kit decisions marked by a field: every CC still starts with the kit's numbers taken, and updates still mean a merge.
- Kit knowledge outside `docs/`: the validator, the links and the knowledge map would need a second root.
- No protection, a convention only: an edited kit note is silently lost at the next update.

## Consequences

- Updating a CC's kit knowledge is a replacement of `docs/kit/`, not a merge.
- An existing CC needs a one-time migration that moves its copies of kit notes into `docs/kit/` and keeps its own decisions where they are.
- A CC that must diverge from the kit says so in its own decision, where the next kit update cannot overwrite it.

## Revisit when

A `cc-kit upgrade` command replaces the kit layer automatically, or a CC needs to diverge from the kit in a way an override decision cannot express.

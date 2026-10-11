---
name: cc-help
description: List the CC's skills by purpose and explain the one the user picks: when to use it, what it does, the commands it runs and what it never does. Use when the user asks for help, what the CC can do, or how a skill works.
---

# CC help

Help is read from the skills themselves, never from memory, so it is always current.

## 1. List

1. Read the frontmatter (`name`, `description`) of every `.agents/skills/*/SKILL.md`. Skip `_shared`. Council and thread roles live in `.agents/roles/` and are loaded by the runners, not listed here; mention once that councils load them automatically.
2. Group the rest and show one short line per skill, numbered across all groups:
   - **Set up and plan:** `grill-*`
   - **Run the CC:** `cc-*` except `cc-help`
   - **Write, test and debug code:** every other skill
3. If the user named a skill or a goal ("how do I fix a bug?"), skip the list and go straight to that skill.
4. Ask which one to explain, by number or name, and wait. Do not explain all of them.

## 2. Explain the chosen skill

Read its `SKILL.md` in full, the files it links to, and its `agents/openai.yaml`. For skills that run `./cc`, also read the matching part of the `./cc help` output. Then explain, short and concrete:

- **What it is for**, in one or two sentences, and when it triggers on its own versus when to ask for it.
- **How it works**, as the steps it actually follows.
- **What it runs**: the `./cc` commands and the files it reads or writes. On Windows show the launcher form (`.\cc ...` in PowerShell).
- **What it never does**: its stop rules, approvals and limits.
- **How to use it**: two or three example requests in plain words, and the direct form (`/name` in Claude Code and Cursor, `$name` in Codex).
- **Related skills** it hands off to.

When it is adapted from another project (an Origin section), name the source and its license in one line.

## 3. Next

Offer to explain another skill or to start the chosen one. Do not start a skill that changes anything until the user asks.

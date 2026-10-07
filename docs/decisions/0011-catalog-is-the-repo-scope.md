---
id: decision.0011-catalog-is-the-repo-scope
title: The catalog is the CC's repo scope, managed by link
status: accepted
summary: A CC's repositories are exactly its catalog; ../repos/ is shared between CCs and is never scanned. Repos are added by pasting a link (main branch read from the remote), removed, re-branched and marked project or reference through ./cc repo and the settings panel; ./cc prs lists open PRs of catalog repos only.
verified_at: 2026-10-07
evidence:
  - scripts/repositories.py
  - scripts/repositories_test.py
  - scripts/prs.py
  - scripts/prs_test.py
  - scripts/settings/app.py
  - .agents/skills/cc-prs/SKILL.md
  - .agents/skills/_shared/cc-cli.md
relations:
  - docs/index.md
  - docs/rules/worktrees.md
  - docs/rules/project-adapters.md
---

# The catalog is the CC's repo scope, managed by link

## Context

Several CCs (for example pv_CC and di_CC) sit in one parent folder and share `../repos/`. Asked for "new PRs", agents in both CCs looped `gh pr list` over every clone in `../repos/` and mixed the other CC's repos in. Nothing executable stated the scope, and the topology rule pointed at the shared folder. Separately, a repo's main branch is not always `main`, and some repos (a PoC) are guidance only.

## Decision

- The catalog (`catalog/repositories/*.json`, `./cc repo list`) is the only list of a CC's repos. Agents never enumerate `../repos/` or `../worktrees/`; the rule is in `AGENTS.md` and the shared skill note.
- `./cc prs` lists open PRs of catalog repos only, newest first, marking PRs not seen or changed since the last listing (`.cc-local/prs-seen.json`, per machine). The `cc-prs` skill shows them and lets the user pick one from a choice list.
- `./cc repo add <url>` derives the id from the link and reads the main branch from the remote's HEAD; `remove`, `set-branch` (checked against the remote), `set-remote` and `set-kind` complete the set. The settings panel's Repos tab runs the same commands.
- `kind: reference` marks read-only guidance: no targets, stack or adapter, skipped by `./cc verify`, refused by `./cc worktree`.
- `/cc-settings` opens the `./cc settings` panel in a terminal (the desktop app's Terminal panel) rather than imitating it in the chat; the chat version remains for sessions that cannot open a terminal.

## Options considered

- Giving each CC its own `repos/` folder: isolates clones, but duplicates them and changes the agreed topology.
- A memory or prose note per CC: per machine and per agent, and does not survive the next agent.

## Consequences

- `./cc prs` needs an authenticated `gh` in the environment `./cc` runs in (WSL on Windows).
- `remove` keeps the base clone and any Nix adapter: other CCs may share the clone, and adapter removal is a deliberate Nix change.

## Revisit when

A CC needs repos from a forge other than GitHub in `./cc prs`, or CCs stop sharing a parent folder.

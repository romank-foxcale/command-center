---
id: decision.0009-trello-on-demand
title: Trello cards are updated on demand, with credentials outside every repository
status: accepted
summary: A CC can connect one Trello board and link cards to plans and features, but it only comments on or moves a card when the user asks, after a preview; the API key and token live in ~/.config/cc/trello.env.
verified_at: 2026-10-06
evidence:
  - scripts/trello.py
  - scripts/trello_test.py
  - scripts/validate-control-center.py
  - .agents/skills/cc-trello/SKILL.md
relations:
  - docs/index.md
  - docs/decisions/0007-agent-councils.md
---

# Trello cards are updated on demand, with credentials outside every repository

## Context

Teams track work on Trello boards, while the CC knows the plans, features, verify results and council verdicts. Copying those by hand is tedious, but whatever lands on a card is visible to the whole team, so it must be deliberate.

## Decision

- `catalog/integrations/trello.json` holds the board and maps plan states to lists (`active`, `completed`). Plans link a card with a `Trello: <url>` line; features with `trelloCard` in their worktree manifest.
- `./cc trello comment` and `./cc trello move` only preview unless given `--yes`; the `cc-trello` skill shows the preview and waits for the user's yes to that exact preview. Nothing is posted as a side effect of another command.
- Credentials are read from `~/.config/cc/trello.env` (or the environment), never written by the CC, never printed in errors, and rejected by `./cc check` if they appear in the catalog.
- It uses Trello's REST API directly, so it works the same from Claude Code, Codex and the terminal.

## Options considered

- Claude's Trello connector: no token to manage, but unavailable to Codex and `./cc` commands.
- Automatic updates on plan transitions and council results: convenient, but posts things the user did not review.

## Consequences

- Each user needs their own Trello key and token on each machine.
- Card links on features are local to the machine, like the worktree manifests that hold them.

## Revisit when

The team wants a specific automatic update, for example moving a card when a plan completes; it would need an explicit per-CC opt-in.

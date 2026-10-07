---
id: decision.0005-multi-tool-agent-configs
title: One set of skills for every AI tool
status: accepted
summary: Skills live in .agents/skills, Claude Code gets a checked copy in .claude/skills, and instructions stay in AGENTS.md.
verified_at: 2026-10-07
evidence:
  - scripts/agent-configs.py
  - CLAUDE.md
  - .agents/skills/grill-cc-bootstrap/SKILL.md
  - .claude/skills/grill-cc-bootstrap/SKILL.md
  - flake.nix
relations:
  - docs/index.md
  - docs/decisions/0003-template-as-seed.md
  - docs/rules/bootstrap.md
  - docs/decisions/0013-rule-hooks.md
---

# One set of skills for every AI tool

## Context

People open the CC in Claude Code, Cursor, Codex and OpenCode. Codex reads project skills only from `.agents/skills`, Claude Code only from `.claude/skills`; Cursor and OpenCode read both folders. Every tool reads `AGENTS.md`, except Claude Code when a `CLAUDE.md` exists.

## Decision

- The canonical skills are in `.agents/skills/`.
- `.claude/skills/` is a copy created by `./cc agents sync`; `./cc check` fails if they differ.
- `CLAUDE.md` contains only `@AGENTS.md`.
- A copy rather than a symlink: a symlink breaks when the repo is cloned on Windows without WSL.

## Consequences

- Cursor and OpenCode see the same skills twice; the contents are identical.
- Editing the copy in `.claude/skills/` without editing the source breaks the check.
- `.opencode/skills` is not used: OpenCode reads `.agents/skills`.
- `./cc agents sync` also writes the `hooks` key of `.claude/settings.json`; hooks are Claude Code only ([0013](0013-rule-hooks.md)).

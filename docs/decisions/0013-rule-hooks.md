---
id: decision.0013-rule-hooks
title: Claude Code hooks enforce the hard rules early; the gates still decide
status: accepted
summary: The AGENTS.md hard rules that a tool call reveals are enforced by Claude Code hooks at the moment of the call, and every rule that leaves an artifact is also gated by ./cc check or ./cc verify, so other tools and missed hooks are still caught.
verified_at: 2026-10-07
evidence:
  - scripts/rule_hooks.py
  - scripts/rule_hooks_test.py
  - scripts/hook
  - scripts/agent-configs.py
  - scripts/validate-knowledge.py
  - scripts/verify.py
  - .claude/settings.json
relations:
  - docs/index.md
  - docs/decisions/0005-multi-tool-agent-configs.md
  - docs/rules/worktrees.md
---

# Claude Code hooks enforce the hard rules early; the gates still decide

## Context

The hard rules in `AGENTS.md` were instruction text only. Agents break them when a tool default disagrees: Claude Code appends an AI `Co-Authored-By` trailer to commits, agents reach for `cmake` or `pytest` instead of Nix, and they edit the generated `.claude/skills` copy. Gates found some of this late; some of it nothing found.

## Decision

- `scripts/rule_hooks.py` holds the hook logic; `scripts/hook` runs it with the first working Python (`python3`, `python`, `py -3`), because on native Windows `python3` is often the Store stub.
- `./cc agents sync` owns the `hooks` key of `.claude/settings.json` (every other key stays the user's); `./cc agents check` fails when it was edited by hand.
- What each hook does and the gate behind it:

  | Rule | Hook | Gate |
  | --- | --- | --- |
  | No AI credit in commits or PRs | deny `git commit`, `gh pr create/edit` with an AI `Co-Authored-By` or "Generated with" line | `./cc verify` scans branch commits in the CC and each feature worktree |
  | No direct build or test tools | `ask`: the user approves a diagnosis run | none: a command leaves no artifact |
  | Skills only in `.agents/skills` | deny edits under `.claude/skills` | `agent-configs` check |
  | No stray Markdown | deny creating `.md` outside `docs/`, `plans/`, the skills, `templates/` and the root files | `knowledge` check |
  | Notes follow the knowledge rules | after an edit in `docs/`, return that note's validation errors | `knowledge` check |
  | Skill copies in sync | at stop, report drift once | `agent-configs` check |

- A hook that fails warns and never blocks (exit 1, not 2): a broken hook must not stop work, and the gate is still there.

## Options considered

- Rules as text only: the status quo that let attribution trailers through.
- Git `commit-msg` hooks: they work for every tool, but setting `core.hooksPath` in project repos overrides the projects' own hooks.
- A SessionStart hook against sessions started in a worktree: such a session never loads the CC's settings, so it cannot fire. The session guard file written by `./cc worktree` covers this instead.

## Consequences

- Hooks exist only in Claude Code. Codex, Cursor and OpenCode rely on the gates.
- Hooks match shell text, so a command hidden in a script or another shell (`wsl.exe bash -lc ...`) passes the hook; only the gates are complete where a gate exists.
- New CCs get the hooks through `./cc bootstrap install`; existing CCs only through a migration.

## Revisit when

Codex, Cursor or OpenCode gain a hook format worth generating, or a hook blocks legitimate work often enough that its matcher needs a different design.

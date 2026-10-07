# rule-hooks: Claude Code hooks enforce the hard rules, and cc-learn turns solved problems into atomic notes

Lifecycle: completed
Planning status: accepted

## Outcome

1. In a Claude Code session in a CC, the AGENTS.md hard rules that can be detected from a tool call are enforced by hooks at the moment of the call, not only by instruction text. Every rule that leaves a persistent artifact is also gated by `./cc check` or `./cc verify`, so sessions in Codex, Cursor and OpenCode, and sessions where a hook did not fire, are still caught.
2. A `cc-learn` skill turns a non-obvious solved problem from the current session into one atomic note (hack, debt or decision) that passes `./cc validate`, after the user confirms the draft.

## Non-goals

- Hooks for Codex, Cursor or OpenCode. They get the gates only.
- Hooks inside sibling project repos or their worktrees. The hooks live in the CC and fire because sessions start in the CC root (`./cc open`).
- Git `commit-msg` hooks or any change to `core.hooksPath`: they would override project repos' own hooks.
- Auto-formatting, linting or type checking after edits (ECC's Prettier and tsc hooks): quality gates stay in Nix (ADR 0008).
- Session memory files, transcripts or automatic pattern extraction: AGENTS.md forbids storing conversations.
- Automatic saving of learned notes. `cc-learn` always shows the draft and waits for a yes.
- Committing anything. The user commits.

## Evidence and current behavior

- No hooks exist: `.claude/settings.json` holds only a `permissions` allowlist; a search for "hook" outside skills finds none.
- `.claude/settings.json` is tracked; `.claude/settings.local.json` is ignored (`.gitignore`).
- `scripts/agent-configs.py` mirrors `.agents/skills` to `.claude/skills`; `sync` replaces the target tree, `check` reports drift. The Nix check `agent-configs` runs `check` (`flake.nix`).
- Nix checks build from `${self}`, a store copy without `.git`, so they cannot read commit history.
- On native Windows (this desktop app), `python3` in Git Bash resolves to the Microsoft Store stub and fails; `python` (3.13) and `py` work. In WSL, `python3` works. `./cc` itself calls `python3`.
- Tracked Markdown outside `docs/`, `plans/`, `.agents/skills/`, `.claude/skills/`: `AGENTS.md`, `BOOTSTRAP.md`, `CLAUDE.md`, `GUIDE.md`, `README.md`, `templates/*.md`.
- `docs/hacks/index.md` and `docs/debt/index.md` have no entries; `templates/note.md` and `templates/decision.md` exist.
- `./cc validate` runs `scripts/validate-knowledge.py`.
- `./cc bootstrap install` copies every tracked file (`scripts/materialize-template.py`), so new CCs get the hooks and scripts. Existing CCs get them only through a migration; that is out of scope.
- Q1 answered: the Claude Code desktop app on native Windows runs the hook command `"$CLAUDE_PROJECT_DIR"/scripts/hook` through Git Bash; live probes in the implementing session were denied for a stray `.md`, an AI trailer in `git commit` and an edit under `.claude/skills`.
- `cc-help` lists skills from their frontmatter, so it needs no edit for `cc-learn`.
- ECC's equivalents (inline `node -e` hooks, session-end and evaluate-session scripts) are generic or placeholders; only the ideas are reused.

## Affected scope

| Repository | Worktree | Read/write | Interfaces |
| --- | --- | --- | --- |
| command-center (this CC template) | none: branch `rule-hooks` in the CC checkout | write | `.claude/settings.json` `hooks`, `scripts/rule_hooks.py` CLI, `./cc agents sync/check`, `./cc check`, `./cc verify`, new skill `cc-learn` |
| sibling project repos | none | read only, by `./cc verify` commit scan | none changed |

## Invariants and decisions

- Hook logic lives in `scripts/rule_hooks.py` with tests in `scripts/rule_hooks_test.py`, like the existing `*_test.py`. Interface: `rule_hooks.py <event>` reads the Claude Code hook JSON on stdin and writes the hook response on stdout. Events: `pre-bash`, `pre-edit`, `post-edit`, `stop`.
- Decision functions are pure (input JSON → decision) and unit-tested; the CLI wrapper only does I/O.
- The `hooks` block of `.claude/settings.json` is owned by `scripts/agent-configs.py`: `sync` writes it and keeps every other key (permissions) untouched; `check` fails when it differs. Hand edits to that block are drift.
- Hook commands run through a small launcher that picks the first working interpreter of `python3`, `python`, `py -3`. If none works, the hook prints a visible warning and exits non-blocking (fail-open, never silent).
- Rules and how each is enforced:

  | Rule | Hook | Gate for other tools |
  | --- | --- | --- |
  | No AI attribution in commits and PRs | `pre-bash`: deny `git commit`, `gh pr create/edit` whose message or body has `Co-Authored-By:` naming an AI, or "Generated with" | `./cc verify` scans commits on the current branch since its base in the CC and in each feature worktree |
  | No direct `cmake`, `make`, `docker build`, test runners | `pre-bash`: answer `ask` with the reason, so the user approves diagnosis runs and stops the rest | none: a command leaves no artifact, accepted as hook-only |
  | Edit skills only in `.agents/skills` | `pre-edit`: deny Edit/Write under `.claude/skills/` | existing `agent-configs` check |
  | No stray Markdown | `pre-edit`: deny creating `.md` outside the allowlist | new check in `validate-knowledge.py`: tracked `.md` outside the allowlist fails |
  | No session inside a worktree | none: a session started in a worktree never loads the CC's settings, so a CC hook cannot fire. Already covered by the session guard `./cc worktree` writes above each worktree (`scripts/worktrees.py` `write_session_guard`) | none |
  | Notes follow the knowledge rules | `post-edit`: run note validation on an edited `docs/**.md` and return errors to the agent | existing `./cc validate` |
  | Skill copies in sync | `stop`: report drift once per stop | existing `agent-configs` check |

- Markdown allowlist: `docs/**`, `plans/**`, `.agents/skills/**`, `.claude/skills/**`, `templates/*.md`, and the root files `AGENTS.md`, `BOOTSTRAP.md`, `CLAUDE.md`, `GUIDE.md`, `README.md`. It lives in one place in code and both the hook and the check import it.
- Matching is on parsed commands, not substrings: `make` inside `cmake-format` or a path does not match; `git commit -F file` reads the file.
- `cc-learn` writes one note per run from `templates/note.md` (hack, debt) or `templates/decision.md` (decision), into `docs/hacks/`, `docs/debt/` or `docs/decisions/`, adds the entry to that folder's index (decisions to `docs/index.md`), links a hack to a decision or debt and its `remove_when`, and runs `./cc validate`. It shows the full draft and waits for an explicit yes before writing. It refuses trivia, one-off outages and anything already stated in a note (it searches first and offers to update instead). It is suggested only by a closing step of the `debug` skill (after a verified fix with a non-obvious root cause) or run on request; no hook suggests it.
- A new ADR `docs/decisions/0013-rule-hooks.md` records: hooks are an enforcement layer for Claude Code only, the gates remain the source of truth, and why. It extends ADR 0005.

## Open questions

| Question | Impact | Owner/next evidence |
| --- | --- | --- |

## Work packages

| ID | Outcome | Write scope | Depends on | Completion check |
| --- | --- | --- | --- | --- |
| WP1 | Hook decisions and CLI, with the launcher | `scripts/rule_hooks.py`, `scripts/rule_hooks_test.py`, `scripts/hook` (launcher), `flake.nix` (test check) | none | `python3 scripts/rule_hooks_test.py` passes; each rule has a deny and an allow case |
| WP2 | `agents sync` writes and `check` verifies the `hooks` block | `scripts/agent-configs.py`, `scripts/agent_configs_test.py`, `.claude/settings.json` | WP1 interface (fixed above) | tests pass; `./cc agents check` fails after a hand edit of `hooks` and passes after `sync`; `permissions` unchanged |
| WP3 | Gates for persistent artifacts | `scripts/validate-knowledge.py` (Markdown allowlist), `scripts/verify.py` and its test (attribution scan) | none | a stray `.md` fails `./cc check`; a commit with an AI trailer fails `./cc verify` |
| WP4 | ADR and rule text | `docs/decisions/0013-rule-hooks.md`, `docs/index.md`, `AGENTS.md` (one line: hooks enforce, gates decide) | none | `./cc validate` passes |
| WP5 | `cc-learn` skill | `.agents/skills/cc-learn/`, `.agents/skills/debug/SKILL.md` (closing step only) | none | skill passes `./cc agents check` after sync; a dry run on a sample problem produces a note that passes `./cc validate` |
| WP6 | Integration | `.claude/skills/` (sync output only) | WP1–WP5 | see below |

WP1, WP3, WP4 and WP5 can run in parallel; WP2 needs only the fixed CLI interface. `./cc agents sync` runs once, in WP6.

## Integration and verification

- `./cc agents sync`, then `./cc check` and `./cc verify` pass.
- Smoke test in Claude Code in WSL and in the Windows desktop app: a denied `git commit` with an AI trailer, a denied edit under `.claude/skills/`, a denied stray `.md`, a note validation error after a bad note edit, and the drift message at stop.
- Hook latency: each hook returns in under 1 s on WSL.

## Failure, rollback and stop conditions

- A hook that blocks a legitimate command is a bug: fix the matcher with a test, never weaken the rule text.
- Rollback: remove the `hooks` entries from `agent-configs.py` and run `./cc agents sync`; the gates keep working alone.
- Stop and re-plan if Claude Code on native Windows cannot run the launcher (Q1): fall back to supporting hooks in WSL only and record that as debt.

## Acceptance criteria

- Every rule in the table has a passing deny test and allow test.
- `./cc check` fails on skills drift, a hand-edited `hooks` block and a stray `.md`; `./cc verify` fails on an AI attribution trailer.
- Removing Python from PATH makes the hooks warn visibly, not block or stay silent.
- `cc-learn` produces a note that passes `./cc validate` and is linked from its index, and writes nothing without confirmation.
- ADR 0013 is in `docs/index.md`; no AI attribution in any commit of the branch.

## Lifecycle closure

- state: completed
- date: 2026-10-07
- evidence: PR romank-foxcale/command-center#17 merged as 9c60860; ./cc check and ./cc verify passed; hooks denied live probes on native Windows

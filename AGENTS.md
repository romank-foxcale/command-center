# Control Center agent protocol

This repository is the map and executable control plane for its sibling projects.

## Bootstrap trigger

If the user asks to create, configure or migrate a CC:

1. read `BOOTSTRAP.md`;
2. load the `grill-cc-bootstrap` skill;
3. determine the mode: `new` or `migration`;
4. keep grilling until the state is verifiable, not until you get the first answer.

Do not invent a new topology for the CC: base clones live in `../repos/`, feature worktrees in `../worktrees/<feature>/<repo>_wt/`. The CC itself stays in its own root.

If the user asks to plan a complex or agentic task, load `grill-task-planning`. Keep current plans in `plans/active/`, cancelled ones in `plans/archived/` and finished ones in `plans/completed/`; make transitions with `./cc plan`.

## Getting started

1. Read `docs/index.md`.
2. Open only the notes relevant to the task and their direct relations.
3. Run `./cc show` to see the real executable interface.
4. Before making changes, identify the affected projects, workflows and checks.

Do not scan all of `docs/` or the archives without a reason.

## Sources of truth

- Build, tests, packaging, running and deployment: Nix expressions.
- Runtime state: CI/CD, observability and the target system's APIs.
- Reasons, constraints, hacks, decisions and tech debt: atomic Markdown notes.
- Project code: the corresponding sibling repository.
- Secrets: an external secret manager, never this repository.

## Hard rules

- Never write an executable process down as step-by-step Markdown instructions.
- Never fix drift by updating a description: fix the Nix contract or the project.
- Never bypass Nix with direct `cmake`, `make`, `docker build` or test commands, except for diagnosis; move any working command you find into a derivation, check or app.
- Pin remote sources through flake inputs. For local development use an input override, not absolute paths committed to Git.
- Create feature worktrees with `./cc worktree`; build and check them with `./cc feature <feature> ...`.
- Put pure, reproducible actions in `packages`/`checks`; networked, interactive and privileged ones in explicitly run `apps`.
- Production actions are forbidden by default and require a dedicated adapter, a check and confirmation.
- Never store secrets, full conversations or the agent's internal reasoning.
- Edit skills only in `.agents/skills/`, then run `./cc agents sync`: `.claude/skills/` is a generated copy for Claude Code, and `CLAUDE.md` only imports this file.

## Knowledge rules

- Write everything stored in this repository in English: notes, plans, catalog fields, Nix and script comments, output messages and commit messages. This applies even when the conversation is in another language.
- One note is one durable fact, decision, hack or debt.
- Every note has frontmatter: `id`, `title`, `status`, `summary`, `verified_at`, `evidence`, `relations`.
- Relations and evidence are paths from the repository root.
- Explain the "why" and the limits of applicability; do not duplicate code.
- Mark replaced knowledge `superseded` and link it to its successor.
- Link every hack to a decision or tech debt and to its removal condition.

Details: `docs/rules/knowledge-layout.md`.

## Verification

A change is normally finished with:

```bash
./cc check
```

If Nix is unavailable, run `python3 scripts/validate-knowledge.py .` and state explicitly that the Nix part was not verified.

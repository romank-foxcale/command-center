# per-cc-layout: every CC keeps its own repos and worktrees inside its folder, isolated from other CCs

Lifecycle: active
Planning status: accepted

## Outcome

A CC's base clones live in `<cc>/repos/<repo>` and its feature worktrees in `<cc>/worktrees/<feature>/<repo>_wt`, both git-ignored. Nothing is shared between CCs, so an agent in one CC finds no other CC's code by browsing. Existing CCs move over with `./cc migrate-layout`, which keeps every worktree, branch and council run working.

## Non-goals

- Sharing Git objects between CCs (`git clone --reference`). Add it only when a repo is large enough to matter.
- Changing personal_CC's private layout (`../personal/repos`). It moves only if its owner asks.
- Changing how Nix adapters pin sources: the flake inputs stay the same.

## Evidence and current behavior

- docs/decisions/0011-catalog-is-the-repo-scope.md rejected per-CC folders because they "duplicate" clones. Its own context records that agents in pv_CC and di_CC mixed each other's repos from the shared `../repos/`.
- On 2026-10-10 no repo was in two catalogs: di_CC has ai, backend, frontend and processor; pv_CC has pv, pv-backend, pv-frontend and pv-poc. All of `~/Projects/repos` was 33 MB, and `~/Projects/worktrees` was 12 MB. So sharing saved nothing.
- Every script reads the layout from `control-center.json` (`projectsRoot`, `repositories`, `worktrees`). Manifests store paths relative to `projectsRoot`. Council `state.json` stores the absolute worktree path. Each worktree's `.git` file and its base clone's `.git/worktrees/<name>/gitdir` hold absolute paths.
- di_CC `nix/projects/ai.nix` defaults `ENV_FILE` to `../repos/ai/.env`.

## Affected scope

| Repository | Worktree | Read/write | Interfaces |
| --- | --- | --- | --- |
| command_center_template | branch per-cc-layout in place (the template is not a catalog repo) | write | layout contract, scripts, hooks, skills, docs, cc-kit |
| pv_CC | in place | write | kit upgrade, migrate-layout, notes and plans that name old paths |
| di_CC | in place | write | kit upgrade preserving its `editable` extension, migrate-layout, ai.nix ENV_FILE default, notes and plans |

## Invariants and decisions

- Layout: `projectsRoot "."`, `repositories "repos"`, `worktrees "worktrees"`, `worktreePattern "{feature}/{repository}_wt"`. Manifest paths stay relative to `projectsRoot`, so they become `repos/<id>` and `worktrees/<feature>/<id>_wt`.
- `repos/` and `worktrees/` are git-ignored: Nix and `git ls-files` never see them, and ripgrep-based search skips them by default.
- A hook asks before any Read, Grep, Glob, Edit, Write or shell path that resolves into a sibling of the CC folder: another CC, an RC, or the old shared folders. It asks rather than denies, because a user may deliberately work across projects.
- `./cc verify` and `./cc doctor` fail when `repos/` holds a clone the catalog does not list. Nix checks cannot see ignored folders, so that check cannot live in `./cc check`.
- `./cc migrate-layout`:
  - moves only this CC's catalog clones and the features whose manifest names this CC;
  - repairs worktree links with `git worktree repair`;
  - rewrites the manifests, the council state paths and the layout;
  - refuses a clone that another CC's catalog also lists, and anything already present at a destination.
- Decision 0016 records the change. Decision 0011 keeps its catalog rules and points to 0016 for the folder.

## Open questions

| Question | Impact | Owner/next evidence |
| --- | --- | --- |
| Does a session started inside `<cc>/worktrees/<f>/<r>_wt` now load the CC's CLAUDE.md from a parent folder? | Could relax the "always ./cc open" rule | Probe later; the rule and the guard file stay as they are |

## Work packages

| ID | Outcome | Write scope | Depends on | Completion check |
| --- | --- | --- | --- | --- |
| WP1 | New layout contract, ignore rules, messages, cc-kit no longer creates shared folders | templates, scripts, install/cc-kit, .gitignore | - | validator accepts only the new layout |
| WP2 | Sibling-path hook for read, edit and shell | scripts/rule_hooks.py, scripts/agent-configs.py | - | rule_hooks_test covers sibling CC, own repos, outside Projects |
| WP3 | Stray-clone check in verify and doctor | scripts/repositories.py, scripts/verify.py, cc | WP1 | test: an unlisted clone fails verify |
| WP4 | `./cc migrate-layout` with tests on real git worktrees | scripts/migrate_layout.py, cc | WP1 | test moves base and worktree, worktree still works, manifest and state rewritten, foreign feature untouched |
| WP5 | Docs, skills, AGENTS.md, BOOTSTRAP.md, GUIDE.md, decision 0016 | docs, .agents, root | WP1-WP4 | ./cc check |
| WP6 | Upgrade and migrate pv_CC and di_CC; fix their own references | pv_CC, di_CC | WP1-WP5 | in each: ./cc check, ./cc worktree status of every feature, ./cc repo list shows clones present |

## Integration and verification

`./cc check` in the template, plus a migrate-layout test on real git repos. In pv_CC and di_CC: `./cc check`, `./cc repo list` (every clone present) and `git worktree list` in every base clone (no prunable entries).

## Failure, rollback and stop conditions

- Stop if a clone is in two catalogs, or a destination already exists. migrate-layout refuses before moving anything.
- Moves are renames on one filesystem. A failed run is reversed by moving the folders back and running `git worktree repair`.

## Acceptance criteria

- No CC uses `../repos` or `../worktrees`. `~/Projects/repos` and `~/Projects/worktrees` are empty and removed.
- Every feature of pv_CC and di_CC still shows its branch and HEAD, and `./cc check` passes in both.
- An agent's attempt to read `../di_CC` from pv_CC is asked about, not silently allowed.

## Lifecycle closure

Not closed.

---
id: decision.0016-per-cc-repos-and-worktrees
title: Every CC keeps its own repos and worktrees inside its folder
status: accepted
summary: Base clones live in <cc>/repos/project/<repo> or, read-only on disk, <cc>/repos/reference/<repo>, and feature worktrees in <cc>/worktrees/<feature>/<repo>_wt, git-ignored, so no CC can stumble on another's code and every path says whether a repo is the truth or a reference; a hook asks before any tool reaches a sibling folder, verify and doctor fail on clones outside the catalog, and ./cc migrate-layout moves an existing CC.
verified_at: 2026-10-10
evidence:
  - templates/control-center.json
  - scripts/validate-control-center.py
  - scripts/migrate_layout.py
  - scripts/migrate_layout_test.py
  - scripts/rule_hooks.py
  - scripts/repositories.py
relations:
  - docs/rules/worktrees.md
  - docs/decisions/0011-catalog-is-the-repo-scope.md
  - docs/decisions/0013-rule-hooks.md
---

# Every CC keeps its own repos and worktrees inside its folder

## Context

Until now, every CC under one Projects folder shared `../repos/` and `../worktrees/`. The aim was to clone a repo once, even when two CCs use it. In practice it let agents mix projects: agents in pv_CC and di_CC listed each other's PRs ([0011](0011-catalog-is-the-repo-scope.md)). The fix was a prose rule, not a boundary. On 2026-10-10 no repo was in two catalogs, and all shared clones together were 33 MB, so sharing saved nothing.

## Decision

- **Layout.** `control-center.json` uses `projectsRoot "."`, `repositories "repos"` and `worktrees "worktrees"`. Base clones are `repos/<kind>/<repo>`, and worktrees are `worktrees/<feature>/<repo>_wt`. Both folders are git-ignored, so Nix and Git never see them.
- **Validator.** It accepts only this layout. For the old one, it names `./cc migrate-layout`.
- **Hook.** A Claude Code hook (`pre-read` for Read, Grep and Glob, plus the existing edit and shell hooks) asks before a path resolves into a sibling of the CC folder: another CC, an RC, or the old shared folders. It asks rather than denies, because the user may deliberately work across projects.
- **Kind folders.** A clone lives in `repos/project/<id>` or `repos/reference/<id>`, by its catalog kind, so every path an agent reads says what the repo is. Claude, Codex and Cursor all read paths, while only some follow prose rules. `./cc repo set-kind` moves the clone.
- **Reference clones are read-only on disk.** Their files and folders lose write permission (`.git` keeps it, so fetching works). The OS then refuses every writer, whatever tool or rule it follows. `./cc repo update` lifts the protection only for a fast-forward pull.
- **Base clones are never edited.** A Claude Code hook denies edits anywhere under `repos/` and names the feature worktree instead. After the first read of a reference repo in a session, another hook reminds the agent that it is guidance to check against the project repos, not the truth.
- **Stray clones.** `./cc verify` fails, and `./cc doctor` warns, when `repos/` holds a clone the catalog does not list under that kind, or anything besides `project/` and `reference/` (`./cc repo strays`). Nix checks cannot see the ignored folder.
- **Migration.** `./cc migrate-layout` (from the shared folders, or from flat `repos/<id>`) moves only this CC's catalog clones and the features whose manifest names this CC. It repairs worktree links (`git worktree repair`), and rewrites manifests, council run state, session guards, the layout and `.gitignore`. It refuses a clone another CC's catalog also lists, before anything moves.
- **Same repo in two CCs.** It is cloned twice. Sharing objects (`git clone --reference`) waits until a repo is large enough to matter.

## Consequences

- A CC folder now contains other Git repositories. Tools that ignore `.gitignore` can descend into them, while ripgrep-based search, Nix and `git ls-files` skip them.
- Deleting a CC folder deletes its clones and worktrees with it. Push or commit feature work first.
- A read-only reference clone must be made writable (`chmod -R u+w`) before it can be deleted. A process running as root ignores the protection, but agents never run as root.
- The read-only protection is a file mode, so it holds on Linux, WSL and macOS file systems. A clone on a Windows drive (`/mnt/c`) does not keep it, which is one more reason the projects folder lives inside Linux.

## Revisit when

A repo needed by several CCs is large enough that duplicate clones cost real disk or fetch time.

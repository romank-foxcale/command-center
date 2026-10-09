---
name: cc-repo
description: List, show, add (by pasting a link), remove, retarget or change the main branch, link, kind or onboarding status of repositories in the Control Center catalog by running ./cc repo. Use when the user asks which repos the CC knows, wants details on one, adds or removes a repo, says a repo's main branch is develop, changes the platforms a repo ships on (windows, linux, macos), marks a repo as reference-only, or marks it adapted, verified or blocked.
---

# CC repo

First read `../_shared/cc-cli.md` and follow it.

## Commands

| Request | Command |
|---|---|
| Which repos are there? | `./cc repo list` |
| Show repo X | `./cc repo show <id>` |
| Add a repo (pasted link) | `./cc repo add <url> --targets <platform>... --stack <language>... [--branch <name>] [--role "<role>"] [--id <id>] [--clone]` |
| Add a PoC/demo used only as guidance | `./cc repo add <url> --kind reference [--branch <name>]` |
| Remove repo X | `./cc repo remove <id>` |
| X's main branch is develop | `./cc repo set-branch <id> develop` |
| X moved | `./cc repo set-remote <id> <url>` |
| X is only a reference / now a real project | `./cc repo set-kind <id> reference\|project` |
| X now ships on windows and linux | `./cc repo set-targets <id> windows linux` |
| X is written in Java and Kotlin | `./cc repo set-stack <id> java kotlin` |
| Change its status | `./cc repo set-status <id> <discovered\|adapted\|verified\|blocked>` |

## Rules

- `add` derives the id from the link (`foxcope-PV-backend` → `foxcope-pv-backend`) and reads the main branch from the remote; pass `--branch` only when the user names another one, or when the remote cannot be reached.
- Kinds: `project` (default) is built, verified and changed through feature worktrees; `reference` is read-only guidance such as a PoC or demo. It needs no targets, stack or adapter, is skipped by `./cc verify`, and `./cc worktree` refuses it. Ask which kind when the user's words leave it open.
- Targets are the platforms a project repo ships on: `windows`, `linux`, `macos`. Always ask the user; never infer them from CI or the build setup. `set-targets` replaces the whole set.
- After `set-targets`, every target needs a gate in the repo's Nix adapter (`targets.<platform>`); if one is missing, say so and add it through the adapter, then run `./cc verify <id>`. Changing the targets of a verified repo resets it to `adapted`.
- The stack is the repo's languages in lowercase (`java`, `python`, `typescript`, `csharp`, `cpp`, `rust`, ...). Read it from the code when it is unambiguous and confirm it with the user.
- `remove` is **destructive** for this CC's catalog: confirm first. It refuses while a feature worktree uses the repo, and never deletes the base clone in `repos/`; `./cc repo strays` then reports it until it is deleted.
- `set-branch` checks that the remote has the branch; new feature worktrees start from it.
- `--clone` also clones into `repos/<id>`. Ask before cloning.
- Status flow: `discovered` → `adapted` once it has a Nix adapter → `verified` once `./cc verify <id>` passed on every target in this conversation. Otherwise set `blocked` and report the reason.
- Writing the Nix adapter and onboarding a whole CC belong to `grill-cc-bootstrap`; this skill only runs catalog commands.
- In an unbootstrapped template clone, `repo` commands fail on a missing `control-center.json`; point the user to `grill-cc-bootstrap`.

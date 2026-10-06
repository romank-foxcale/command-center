---
name: cc-repo
description: List, show, register, retarget or change the onboarding status of repositories in the Control Center catalog by running ./cc repo. Use when the user asks which repos the CC knows, wants details on one, wants to add a repo, changes the platforms a repo ships on (windows, linux, macos), or marks a repo as adapted, verified or blocked.
---

# CC repo

First read `../_shared/cc-cli.md` and follow it.

## Commands

| Request | Command |
|---|---|
| Which repos are there? | `./cc repo list` |
| Show repo X | `./cc repo show <id>` |
| Add a repo | `./cc repo add <id> --remote <url> --role "<role>" --targets <platform>... --stack <language>... [--branch <name>] [--source-input <input>] [--adapter <path>] [--clone]` |
| X now ships on windows and linux | `./cc repo set-targets <id> windows linux` |
| X is written in Java and Kotlin | `./cc repo set-stack <id> java kotlin` |
| Change its status | `./cc repo set-status <id> <discovered\|adapted\|verified\|blocked>` |

## Rules

- Targets are the platforms the repo ships on: `windows`, `linux`, `macos`. Always ask the user for them when adding a repo; never infer them from CI or the build setup. `set-targets` replaces the whole set.
- After `set-targets`, every target needs a gate in the repo's Nix adapter (`targets.<platform>`); if one is missing, say so and add it through the adapter, then run `./cc verify <id>`. Changing the targets of a verified repo resets it to `adapted`.
- The stack is the repo's languages in lowercase (`java`, `python`, `typescript`, `csharp`, `cpp`, `rust`, ...). Read it from the code when it is unambiguous and confirm it with the user. It picks the default test, property and mutation tools in `docs/rules/quality-gates.md`.
- `add` registers the repo as `discovered`. `--branch` defaults to `main`; `--clone` also clones it into `../repos/<id>`. Ask before cloning.
- Status flow: `discovered` → `adapted` once it has a Nix adapter → `verified` once `./cc verify <id>` passed on every target in this conversation. Otherwise set `blocked` and report the reason.
- Writing the Nix adapter and onboarding a whole CC belong to `grill-cc-bootstrap`; this skill only runs catalog commands.
- In an unbootstrapped template clone, `repo` commands fail on a missing `control-center.json`; point the user to `grill-cc-bootstrap`.

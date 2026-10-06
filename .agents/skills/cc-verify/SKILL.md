---
name: cc-verify
description: Verify, check, build, run or inspect the Control Center and feature worktrees through Nix by running ./cc verify, check, build, run, show, validate, doctor and ./cc feature. Use when the user wants to test, check, verify, build or run something, asks whether code works or is ready to push, wants to see what the CC exposes, validate the knowledge notes, or check the local setup, for the CC itself or for a feature.
---

# CC verify

First read `../_shared/cc-cli.md` and follow it.

## Commands

| Request | Command |
|---|---|
| Does it work? Is it ready to push? | `./cc verify [<repo>...]` |
| Same for feature F | `./cc feature <feature> verify` |
| Quick pure checks only | `./cc check` / `./cc feature <feature> check` |
| Build / run target X | `./cc build <name>` / `./cc run <name> [args]` |
| What can I build, check or run? | `./cc show` |
| Validate the knowledge notes | `./cc validate` |
| Is my setup OK? | `./cc doctor` |

## Rules

- "Works", "tested", "done" and "ready to push" mean `./cc verify` passed: every flake check plus the gate of every target platform the catalog declares (for example the windows gate on the real Windows host). `./cc check` alone does not cover host gates; never report a repo as working on a platform whose gate did not run and pass.
- When a feature worktree is in play, use `./cc feature <feature> ...`; plain commands use the pinned sources, not the worktree. `./cc feature <feature> verify` covers exactly the repos in that feature.
- A `FAIL: no targets.<platform> gate` result means the adapter lacks the gate for a declared platform: report it; the fix is a gate in the adapter, never dropping the target.
- Take target names from `./cc show`; never guess them.
- `run` executes apps, which may use the network or containers. Confirm before running an app that deploys, publishes or touches production; production actions need a dedicated adapter.
- Never bypass Nix with `cmake`, `make`, `msbuild`, `dotnet`, `docker build`, `pytest` or similar to make something pass. A direct command is only for diagnosing a failure, and the fix goes into the Nix contract or the project.
- Output is long; report the final REPO/TARGET/RESULT table and quote the first real failure.
- If the Nix part cannot run, run `./cc validate` and say explicitly that the Nix part was not verified.

# Running the CC CLI

The `cc-*` skills are thin front ends over `./cc`. `./cc` stays the single source of truth: never reimplement its logic, edit its state files by hand, or call the underlying `scripts/*.py` or `nix` directly.

## Invocation

Run every command from the CC root.

- Inside Linux, macOS or WSL: `./cc <command> ...`
- From native Windows: the `cc.cmd` launcher in the CC root runs `./cc` inside WSL with the Nix profile loaded. Use `./cc.cmd <command> ...` from Git Bash, `.\cc <command> ...` from PowerShell, `cc <command> ...` from cmd. It uses the default WSL distribution, or `CC_WSL_DISTRO`.

`./cc` needs bash, Python 3 and, for `check|build|run|show|doctor`, Nix. Never fall back to a Windows-native Python or Git when WSL fails: worktree manifests and Nix overrides must be produced by the same environment that uses them. If WSL or Nix is missing, stop and report it.

## Scope

This CC's repositories are exactly those in `./cc repo list`. Never enumerate or loop over clone folders to answer a question about its repos, PRs or branches; use `./cc repo` and `./cc prs`.

## Behaviour

- Infer arguments from the conversation, active plans and `./cc ... list|status` output; ask only for a required value you cannot infer.
- Report the real output. On failure, quote the error and stop: never retry with other arguments to make it pass.
- Confirm anything the skill marks **destructive** first, naming exactly what will change.

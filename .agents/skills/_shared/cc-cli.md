# Running the CC CLI

The `cc-*` skills are thin front ends over `./cc`. `./cc` stays the single source of truth: never reimplement its logic, edit its state files by hand, or call the underlying `scripts/*.py` or `nix` directly.

## Invocation

Run every command from the CC root.

- Inside Linux, macOS or WSL: `./cc <command> ...`
- From native Windows (Git Bash or PowerShell): `wsl --cd "<CC root as a Windows path>" -- bash -lc './cc <command> ...'`. The login shell (`-l`) is required: without it the Nix profile is not loaded and Nix commands report that Nix is not installed.

`./cc` needs bash, Python 3 and, for `check|build|run|show|doctor`, Nix. Never fall back to a Windows-native Python or Git when WSL fails: worktree manifests and Nix overrides must be produced by the same environment that uses them. If WSL or Nix is missing, stop and report it.

## Behaviour

1. Map the request to the exact `./cc` command; infer arguments from the conversation, the active plans and `./cc ... list|status` output before asking.
2. Ask only for a value that cannot be inferred and that `./cc` requires.
3. Show the command, run it, and report its real output; on failure, quote the error and stop. Do not retry with different arguments to make it pass.
4. Confirm before anything marked **destructive** in the skill, naming exactly what will change.
5. Suggest the next lifecycle step only when the output makes it the obvious one.

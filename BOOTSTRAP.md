# Control Center bootstrap

This file is the first instruction for a model started from the target CC folder.

## Determine the roots

- `template_root` is the folder containing this file; usually `<target_root>/cc_template`.
- `target_root` is the parent of `cc_template`; it becomes the CC.
- Do not change, move or commit `template_root` into the target CC. It is a read-only seed.

Immediately read `<template_root>/.agents/skills/grill-cc-bootstrap/SKILL.md` in full, along with the shared core it references. AI tools do not discover skills inside a child Git repository automatically.

## Determine the mode

If the current folder already has a `control-center.json` with status `discovery` and nothing besides the template files, the CC was already materialized by `cc-kit new`. In that case `template_root` equals `target_root`: do not run the installer, and continue grilling from step 3 of the "New CC" section of the `grill-cc-bootstrap` skill.

- `new`: `target_root` has no CC files apart from `cc_template`. Run from `target_root`:

  ```bash
  ./cc_template/cc bootstrap install .
  ```

- `migration`: `target_root` already has a CC, repository catalog, automation or knowledge in another format. Do not run the installer. First do a read-only inventory, a mapping and a staged migration.

If the mode is unclear, do not write to the target folder until it is clarified.

## Fixed topology

```text
Projects/
├── project1_CC/
├── project2_CC/
├── repos/
│   ├── repo1/
│   └── repo2/
└── worktrees/
    ├── feature1/
    │   ├── repo1_wt/
    │   └── repo2_wt/
    └── feature2/
        └── ...
```

Relative to any `<project>_CC`:

- base checkouts: `../repos/<repo>`;
- worktrees: `../worktrees/<feature>/<repo>_wt`;
- the CC is never copied into a feature folder;
- local absolute paths never end up in Git;
- Nix receives feature sources through `--override-input` from the worktree manifest.

This topology can only be changed by a separate, explicit decision of the user.

In normal work use the executable interface, not manual `git worktree`:

```bash
./cc repo add <repo> --remote <git-url> --role <role> --clone
./cc worktree create <feature> <repo>...
./cc feature <feature> check
./cc worktree status <feature>
./cc worktree remove <feature>
```

`worktree remove` never forces and refuses to work on dirty or unpublished state.

## Acceptance criteria

Do not declare the bootstrap finished until:

1. `control-center.json` and the catalog reflect the agreed model.
2. Every connected repository has a pinned source, a Nix adapter and a check.
3. Workflows consume declared outputs instead of duplicating build commands.
4. Unknown facts are explicitly marked and contradictions are resolved.
5. `./cc bootstrap validate` and `./cc check` pass, or the unverified environment is explicitly recorded.
6. The target CC does not depend on the contents of `cc_template/`.

After that, tell the user that `cc_template/` can be deleted. Do not delete it yourself.

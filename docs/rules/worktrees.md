---
id: rules.worktrees
title: Feature worktree topology
status: active
summary: Base clones are shared between CCs and live in Projects/repos, while the repos a task changes live in Projects/worktrees/feature/repo_wt.
verified_at: 2026-07-21
evidence:
  - BOOTSTRAP.md
  - scripts/worktrees.py
  - cc
  - templates/control-center.json
  - .agents/skills/grill-task-planning/SKILL.md
relations:
  - docs/index.md
  - docs/architecture/control-center.md
  - docs/rules/bootstrap.md
  - docs/rules/project-adapters.md
  - docs/rules/task-planning.md
---

# Feature worktree topology

## Invariant

```text
Projects/
├── <project>_CC/
├── repos/<repo>/
└── worktrees/<feature>/<repo>_wt/
```

The base checkout is used for syncing and for creating worktrees; feature changes are never made in it. One feature folder groups only the repos changed by one task.

## Relation to Nix

The feature manifest in `../worktrees/<feature>/` maps the catalog ID, base checkout, worktree, branch and HEAD. The CC turns the manifest into `--override-input <sourceInput> path:<worktree>`. The Nix adapter stays the same; only the source changes.

`./cc feature <feature> check|build|run` passes the overrides to Nix automatically.

## Safety

Removing a worktree is refused when there is dirty state, unpublished commits, or a mismatch between the manifest and the Git state. Absolute paths and the current state of worktrees are never committed to the CC.

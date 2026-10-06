---
id: rules.worktrees
title: Feature worktree topology
status: active
summary: Base clones are shared between CCs and live in Projects/repos, while the repos a task changes live in Projects/worktrees/feature/repo_wt. Coding sessions start in the CC with ./cc open, because a session started inside a worktree loads none of the CC skills or rules.
verified_at: 2026-10-06
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

## Sessions start in the CC

A Claude Code or Codex session started inside `<repo>_wt` sees only that repository: none of the CC's skills, and none of its `AGENTS.md` rules (verified 2026-10-06 with both CLIs; Codex reads neither from a worktree nor from an added directory). Coding sessions therefore start with `./cc open <feature>`: the tool runs in the CC root with the feature's worktrees added as writable directories and a short feature context (worktrees, verify command, read each repository's own instructions).

As a safety net, `./cc worktree create|add` writes `../worktrees/<feature>/CLAUDE.md`, outside every repository and never committed. A Claude session started in a worktree reads it and stops to ask for a restart; Codex has no such net.

## Safety

Removing a worktree is refused when there is dirty state, unpublished commits, or a mismatch between the manifest and the Git state. Absolute paths and the current state of worktrees are never committed to the CC.

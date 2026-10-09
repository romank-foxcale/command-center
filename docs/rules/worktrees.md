---
id: rules.worktrees
title: Feature worktree topology
status: active
summary: Each CC keeps its base clones in <cc>/repos and the repos a task changes in <cc>/worktrees/feature/repo_wt, both git-ignored and never shared with another CC. Coding sessions start in the CC with ./cc open, because a session started inside a worktree does not get the CC's skills.
verified_at: 2026-10-10
evidence:
  - BOOTSTRAP.md
  - scripts/worktrees.py
  - scripts/migrate_layout.py
  - cc
  - templates/control-center.json
  - .agents/skills/grill-task-planning/SKILL.md
relations:
  - docs/index.md
  - docs/architecture/control-center.md
  - docs/rules/bootstrap.md
  - docs/rules/project-adapters.md
  - docs/rules/task-planning.md
  - docs/decisions/0016-per-cc-repos-and-worktrees.md
---

# Feature worktree topology

## Invariant

```text
Projects/
├── <project>_CC/
│   ├── repos/<repo>/                    (git-ignored base clones)
│   └── worktrees/<feature>/<repo>_wt/   (git-ignored feature worktrees)
└── <other>_CC/
    └── ...                              (its own repos and worktrees, never this CC's)
```

The base checkout is used for syncing and for creating worktrees; feature changes are never made in it. One feature folder groups only the repos changed by one task. Nothing outside the CC folder is this CC's: see [0016](../decisions/0016-per-cc-repos-and-worktrees.md). A CC still on the old shared `../repos` and `../worktrees` moves with `./cc migrate-layout`.

## Relation to Nix

The feature manifest in `worktrees/<feature>/` maps the catalog ID, base checkout, worktree, branch and HEAD. The CC turns the manifest into `--override-input <sourceInput> path:<worktree>`. The Nix adapter stays the same; only the source changes.

`./cc feature <feature> check|build|run` passes the overrides to Nix automatically.

## Sessions start in the CC

A Claude Code or Codex session started inside `<repo>_wt` sees only that repository: none of the CC's skills, and none of its `AGENTS.md` rules (verified 2026-10-06 with both CLIs, when worktrees lived outside the CC; not re-verified for the nested layout). Coding sessions therefore start with `./cc open <feature>`: the tool runs in the CC root with the feature's worktrees added as writable directories and a short feature context (worktrees, verify command, read each repository's own instructions).

As a safety net, `./cc worktree create|add` writes `worktrees/<feature>/CLAUDE.md`, outside every repository and never committed. A Claude session started in a worktree reads it and stops to ask for a restart; Codex has no such net.

## Safety

Removing a worktree is refused when there is dirty state, unpublished commits, or a mismatch between the manifest and the Git state. Absolute paths and the current state of worktrees are never committed to the CC.

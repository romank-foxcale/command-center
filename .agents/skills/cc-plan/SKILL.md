---
name: cc-plan
description: List, show, create, accept, archive or complete task plans with ./cc plan. Use when the user asks about plans, records or approves one, drops one, or reports a planned task finished. To work out a plan's content, use grill-task-planning.
---

# CC plan

First read `../_shared/cc-cli.md` and follow it.

## Commands

| Request | Command |
|---|---|
| What plans are there? | `./cc plan list` |
| Show plan X | `./cc plan show <task-id>` |
| Record a plan | `./cc plan create <task-id> --title "<outcome>"` |
| The plan is agreed | `./cc plan accept <task-id>` |
| Drop the plan (**destructive**) | `./cc plan archive <task-id> --reason "<reason>"` |
| The task is done (**destructive**) | `./cc plan complete <task-id> --evidence "<evidence>"` |

## Rules

- A task id is lowercase hyphen-case and also names the feature worktree folder; propose one from the outcome and reuse it everywhere.
- `--title`, `--reason` and `--evidence` are single non-empty English lines.
- `create` only scaffolds the plan from the template. Its content comes from `grill-task-planning`; do not invent it here.
- `accept` only after the user explicitly agrees with the plan in this conversation. Silence or "looks fine so far" is not agreement.
- `complete` requires an accepted plan and real evidence: a passing `./cc feature <task-id> verify` (or `./cc verify`), a merged PR, or another observable result. Never write evidence that was not observed.
- When a plan with a `Trello:` card is accepted or completed, offer to move its card (`cc-trello`); never move or comment without the user's yes.
- Archived and completed plans are final; never move a plan back or copy it between states.

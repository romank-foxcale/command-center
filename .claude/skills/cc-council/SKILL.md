---
name: cc-council
description: Run, approve, reject or inspect multi-model coding and testing councils (Claude and GPT propose, an anonymous judge decides, a writer implements, ./cc verify gates) with ./cc council, and change which provider and model each agent role uses. Use when the user wants a council to implement or test something on a feature, approves or rejects a council verdict, asks about council runs, or wants a role such as judge or writer to use another model.
---

# CC council

First read `../_shared/cc-cli.md` and follow it.

## Commands

| Request | Command |
|---|---|
| Implement X on feature F | `./cc council run coding --feature <feature> [--repo <repo>] --task "<task>"` |
| Write tests for X on feature F | `./cc council run testing --feature <feature> [--repo <repo>] --task "<task>"` |
| Go ahead / approve | `./cc council approve <run-id>` |
| Use proposal B instead / change something | `./cc council approve <run-id> [--pick <label>] [--note "<instruction>"]` |
| Stop this run | `./cc council reject <run-id>` |
| What runs are there? / show run R | `./cc council status [<run-id>]` |
| Are my subscriptions logged in? | `./cc doctor` |

## Rules

- The feature worktree must exist (`cc-worktree`) and be clean; the council refuses uncommitted changes. A plan work package makes the best task: pass it with `--task-file`.
- Write the task as an outcome with constraints and acceptance, not as a design: the proposers design.
- A run stops after the verdict. Show the user the verdict and the hidden proposal authors, and wait for an explicit decision; never approve on the user's behalf.
- Runs take minutes. Run them in the background when the tool allows it and report the final stage line and the artifacts folder.
- Councils verify with `--quality`. A `done` summary that ends in `WARNING: mutation gate missing` means the tests were not checked against injected bugs; repeat that warning to the user. "tests pass but miss injected bugs" means the mutation gate failed.
- Final stages: `done` (verify passed; the user reviews `changes.diff` and commits), `verify-failed` (report the log; for testing it means suspected bugs), `blocked-security` (report `security.md`), `rejected`, `failed`. Never commit, push or fix things after the run on your own.

## Roles and models

Roles are `catalog/agents/<role>.json`: `provider` (`claude` or `codex`), `model`, `access` (`read-only` or `write-worktree`), `skills`. Councils are `catalog/councils/<name>.json` and name the roles for `proposers`, `judge`, `writer` and `security`, plus `approval` and `maxRetries`.

- To change a model, edit the `model` (and `provider`) field of that role, then run `./cc bootstrap validate`. List Codex models with `codex debug models`; Claude accepts aliases such as `opus` and `sonnet` or full model ids.
- Proposers, judge and security must stay `read-only`; only the writer is `write-worktree`. Validation enforces this.
- A council needs at least two proposers. Using the same provider for every proposer defeats the point; warn the user if they ask for it.

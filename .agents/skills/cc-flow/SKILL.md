---
name: cc-flow
description: Draft, re-verify or list runtime flows - how a catalog project runs for one trigger (startup, a request, a job, a message, and later flows across repos) - as notes in docs/flows whose steps cite the code as repo:<id>/<path>#<symbol>, traced from the project's code and written only after the user confirms each flow. Use when the user wants to map how an app or repo runs, asks for an app roadmap or flow, when ./cc check fails on repo evidence, or when cc-review reports that a flow step no longer holds.
---

# CC flow

A flow tells agents what the code alone does not show quickly: the order in which it runs. It is only worth having while it is true, so every step cites the code that performs it and `./cc check` fails when cited code is gone ([0017](../../../docs/decisions/0017-runtime-flows.md)). Read `docs/rules/knowledge-layout.md` and `templates/flow.md` first.

## Draft

1. **Repository.** Pick it from `./cc repo list`. It must be kind `project` with an adapter (status `adapted` or `verified`); otherwise stop: its code cannot be cited until it is onboarded (`cc-repo`). Read its code in `repos/project/<id>`, never in a worktree, which is deleted.
2. **Candidates.** Find the entry points: startup and `main`, HTTP or RPC routes, CLI commands, message consumers, schedulers, framework hooks, config loading. Propose up to five flows, one line each (trigger → outcome), and ask the user which matter. They know which flows changes keep touching; the code does not.
3. **Trace one flow at a time** from its entry point, in execution order:
   - Keep the steps a change needs to know about: order, async boundaries, where config and state come from, calls to other repos or external services. Drop plumbing.
   - For each step write what happens and why there, and cite it as `repo:<id>/<path>#<symbol>`, where the symbol is stable text in the file: a function, class, route or config key. Never a line number.
   - Only what the code shows. Mark anything you inferred but could not trace, and ask about it.
4. **Confirm.** Show the diagram and the steps and ask the user to confirm or correct them. Write nothing without an explicit yes.
5. **Write** `docs/flows/<name>.md` from `templates/flow.md`, in English: `id` `flows.<name>`, `status: active`, `verified_at` today, every citation of the text listed in `evidence`. Add a row to `docs/flows/index.md`. Run `./cc validate`. If a citation fails, correct the citation; never drop a step to make it pass.

## Re-verify

When `./cc check` reports that a cited file or symbol is gone, when `cc-review` reports that a step no longer holds, or when the user asks:

1. Re-trace the flow from its entry point in the current code: the base clone, or the feature's worktree when the change is on a feature.
2. Show the user what changed, step by step (removed, moved, renamed, new), and ask for confirmation.
3. Update the steps, the evidence and `verified_at`. If the flow no longer exists, set `status: superseded`, link its replacement if there is one, and update its index row.
4. Run `./cc validate`.

## List

Show `docs/flows/index.md`: each flow with its repositories, trigger and `verified_at`. Offer to re-verify the oldest.

## Never

- Write a flow, or change one, without the user's confirmation.
- Cite a reference repository, a `worktrees/` path or a line number.
- Restate code, build or test commands: a flow is order and reasons.
- Change project code: a flow follows the code, never the reverse.

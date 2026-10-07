---
id: decision.0007-agent-councils
title: Agent roles and councils bound to models
status: accepted
summary: The CC assigns a provider CLI and model to each agent role, and runs coding, testing and debug councils in which Claude and GPT propose or diagnose, an anonymous judge decides, the user approves and a writer implements under ./cc verify.
verified_at: 2026-10-06
evidence:
  - scripts/council/run.py
  - scripts/council/providers.py
  - scripts/validate-control-center.py
  - templates/agents/writer.json
  - templates/councils/coding.json
  - templates/councils/debug.json
  - .agents/skills/cc-council/SKILL.md
relations:
  - docs/index.md
  - docs/decisions/0005-multi-tool-agent-configs.md
  - docs/decisions/0006-target-platform-gates.md
  - docs/rules/task-planning.md
  - docs/decisions/0010-live-run-events.md
---

# Agent roles and councils bound to models

## Context

One model's blind spots go unchallenged when it designs, writes and judges its own code. The user holds Claude and ChatGPT subscriptions and wants both to work on the same task, with a chosen model per task type. Earlier the CC never chose a model; each person picked one in their own tool.

## Decision

- A role is `catalog/agents/<role>.json`: provider CLI (`claude` or `codex`), model, access (`read-only` or `write-worktree`) and role skills. A council is `catalog/councils/<name>.json`: the roles that fill a fixed pipeline, `approval` and `maxRetries`.
- `./cc council run` executes the pipeline as headless CLI calls under the user's own subscription logins: proposers in parallel, a judge that sees only shuffled labels, a pause for user approval, the writer, `./cc feature <feature> verify` with bounded retries, then a security review.
- Access is enforced by CLI flags, not prompts: Claude gets a fixed tool set without Bash, and Codex runs in its OS sandbox with temporary directories excluded. Only the writer can edit, and only inside the feature worktree.
- Proposers, judge and writer share the `lean-code` skill, adapted from Ponytail (MIT): read fully, then stop at the first rung of the reuse ladder that holds. It also applies to interactive coding. Test writers and the judge share the `tdd` skill, and failures are investigated with the `debug` skill, both adapted from Superpowers (MIT).
- The debug council gives every role the CC's own verify output as evidence, and the runner enforces red before green: the writer's reproduction test must fail on the unfixed code, must stay unchanged during the fix, and three failed fixes stop the run.
- The CC still holds no credentials and never falls back to another provider or model when one is logged out.
- Run artifacts live in `../worktrees/<feature>/.cc-runs/`, outside Git. Councils never commit or push.

## Options considered

- The interactive session conducts the council: quicker, but its behaviour depends on which tool and session runs it, and the process would live in Markdown.
- A Paperclip-style system of long-running, messaging agents: more general, but far more machinery than a fixed pipeline needs.

## Consequences

- A council costs several model calls per task and can hit subscription rate limits.
- Provider CLI flags change between versions; `providers.py` must follow them, and a broken flag fails the run instead of loosening a restriction.
- The writer cannot run commands, so it relies on `./cc verify` output for feedback.

## Revisit when

A provider offers a stable programmatic interface for subscription use, or councils for planning or security review are needed.

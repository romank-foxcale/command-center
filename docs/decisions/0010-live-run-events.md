---
id: decision.0010-live-run-events
title: Long runs report progress, agent talk and stalls as a live event stream
status: accepted
summary: Councils and ./cc verify append steps, handoffs between agents, what agents say, stalls after 3 minutes of silence and the end to an events.jsonl that ./cc watch follows, so the user never has to ask how a run is going.
verified_at: 2026-10-06
evidence:
  - scripts/events.py
  - scripts/events_test.py
  - scripts/council/run.py
  - scripts/council/providers.py
  - scripts/verify.py
  - .agents/skills/cc-council/SKILL.md
  - .agents/skills/cc-verify/SKILL.md
relations:
  - docs/index.md
  - docs/decisions/0007-agent-councils.md
---

# Long runs report progress, agent talk and stalls as a live event stream

## Context

Council runs and verify take minutes. Started in the background from a chat, they showed nothing until someone asked for status: the user could not see which step ran, what the agents told each other, or whether an agent had hung until the 60-minute timeout.

## Decision

- Every long `./cc` process appends one JSON line per event to an `events.jsonl` in its run folder: a council's `.cc-runs/<run>/`, or `.cc-local/runs/<run>/` for a standalone verify. A verify started by a council writes into the council's stream (`CC_EVENTS`).
- Events are steps, handoffs (whose output goes to which agent), what agents say, agent start and finish, gate results, warnings, errors, stalls and the end. Tool calls stay in the per-agent logs: in a chat they would drown the conversation.
- A watchdog reports a stall when an agent's log or a gate's output is silent for 3 minutes, naming the last thing it did, and repeats every further 3 minutes.
- A crash marks the council run failed and ends the stream; `./cc watch` also ends with an error when the writing process died without an end event.
- `./cc watch [<run>]` follows a stream and exits with the run's result. A chat agent that starts a long run in the background starts this watch too and relays each event.
- Codex runs with `--json` so its commands and messages are parsed like Claude's stream-json.

## Options considered

- Polling `./cc council status` from the chat: works only for councils and reports state, not the conversation or stalls.
- Streaming every tool call: complete, but too chatty to read.

## Consequences

- A 3-minute silence can be a model thinking or a quiet compile, not a hang: a stall is a warning, not a failure.
- The Codex JSON event names follow the CLI version; an unknown event is ignored, so a CLI change loses detail rather than failing a run.

## Revisit when

Agents need to talk to each other directly instead of through the fixed pipeline, or the chat tools gain a native progress display.

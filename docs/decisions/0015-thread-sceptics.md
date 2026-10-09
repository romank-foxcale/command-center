---
id: decision.0015-thread-sceptics
title: Review conversations are judged by two anonymous sceptics, and a judge settles only their splits
status: accepted
summary: Comments on the user's PRs, and replies to the user's comments on other PRs, are judged per thread by two fresh read-only sceptics from different model families, who see the claim, the code at the PR head and the CC notes but never who anyone is. When they agree, their verdict stands. When they split, a judge from a third family decides and the split stays visible. The burden of proof is on the claim, and nothing is posted without the user's yes.
verified_at: 2026-10-09
evidence:
  - scripts/threads.py
  - scripts/threads_test.py
  - scripts/prs.py
  - scripts/council/providers.py
  - scripts/validate-control-center.py
  - templates/councils/threads.json
  - templates/agents/sceptic-claude.json
  - templates/agents/sceptic-grok.json
  - templates/agents/sceptic-judge.json
  - .agents/skills/thread-sceptic/SKILL.md
  - .agents/skills/cc-threads/SKILL.md
relations:
  - docs/index.md
  - docs/decisions/0012-review-bar.md
  - docs/decisions/0014-cursor-provider-and-security-council.md
  - docs/decisions/0007-agent-councils.md
---

# Review conversations are judged by two anonymous sceptics, and a judge settles only their splits

## Context

The CC checks its own claims: councils judge proposals, and `cc-review` refutes its own findings before reporting them (ADR 0012). It did not check claims made by other people: a reviewer's comment on the user's PR, or an author's "fixed" in reply to the user's comment. An agent asked about those in the user's session knows whose PR it is and tends to side with the user, or with whoever spoke last. Cloudflare's security-audit-skill names the remedy: the agent that checks a claim is never the one that made it, and its job is to disprove it.

## Decision

- **Scope:** `./cc prs judge <repo> <n>` covers inline review threads, review summaries and top-level comments, from humans and bots alike.
  - On the user's PR, the claims are other people's comments. Verdicts: `VALID`, `OUT-OF-SCOPE`, `REFUTED`, `NEEDS-INFO`, `PREFERENCE`.
  - On someone else's PR, the claims are replies after the user's latest comment. Verdicts: `ADDRESSED`, `NOT-ADDRESSED`, `PUSHBACK-HOLDS`, `PUSHBACK-FAILS`.
- **Selection:** by default, open threads and any thread with a comment since its last judgment. A resolved thread is trusted until its next comment.
- **Discovery:** `./cc prs` marks the PRs where something waits on the user.
- **Two sceptics:** the `threads` council (`catalog/councils/threads.json`) names them, `sceptic-claude` and `sceptic-grok` by default. They run read-only, one call per thread each, in parallel, each without the other.
- **What a sceptic sees:**
  - people only as `PR author` and `Commenter A`, `Commenter B`, ..., with logins replaced in the bodies too;
  - each comment fenced as data;
  - the code at the PR head, through the review checkout;
  - one summary line per current CC note.
- **Burden of proof:** it lies on the claim, with the bar of ADR 0012. A verdict on the code without an evidence line doesn't count.
- **Agreement:** when every sceptic gives the same verdict, it stands with their evidence merged and no judge call.
- **Splits:** when the sceptics differ, or one is unusable, `sceptic-judge` (GPT by default) gets their replies as anonymous `Review A`, `Review B` in random order and checks the disputed point. Its verdict is marked `split`, and both sceptics' verdicts are shown with it, so the user knows the claim is contested. A thread with no usable final verdict is `UNJUDGED`, never guessed.
- **One Cursor copy per run:** all Cursor calls of a run share one snapshot of the review worktree (ADR 0014's confinement). Its fingerprint is checked after each phase, and a write voids every Cursor verdict of that phase.
- **Local state:** `.cc-local/threads/<repo>-<n>.json` keeps only, per thread, the id of the last comment judged and the verdict. It keeps no comment bodies, prompts or replies.
- **Posting:** drafted replies stay in the chat. Posting, resolving or approving needs the user's yes on the exact text.

## Options considered

- **One sceptic per thread:** cheapest, but one model's blind spots decide alone, and a contested comment looks settled.
- **A judge on every thread:** three calls per thread, when most threads (typos, "fixed in ...") need no summary.
- **The session's own subagent:** works only in tools that have subagents, enforces read-only by prompt rather than by the provider, and its model can't be configured.

## Consequences

- **Cost:** about two calls per judged thread, plus one per split. Only new comments are judged again.
- **Provider logins:** a judge run needs every provider of the threads council logged in. It stops instead of silently dropping a sceptic.
- **Anonymity limits:** logins inside bodies are replaced, but a bot's signature text or a person's writing style can still hint at who wrote a comment. Anonymity removes the login, not every clue.
- **Code at a different commit:** the sceptics read the code at the review checkout, which follows the PR's latest push. A comment on an outdated line is judged against the head.

## Revisit when

Splits are frequent and the judge often sides against the evidence (re-check the skill), or agreeing verdicts turn out wrong (a third sceptic, or a judge on every thread).

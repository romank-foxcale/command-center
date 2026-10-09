---
name: cc-threads
description: Judge the review conversation of a catalog PR with ./cc prs judge. On the user's own PR, it judges other people's comments (bots included) as VALID, OUT-OF-SCOPE, REFUTED, NEEDS-INFO or PREFERENCE. On someone else's PR, it judges the replies to the user's comments as ADDRESSED, NOT-ADDRESSED, PUSHBACK-HOLDS or PUSHBACK-FAILS. Two anonymous sceptics judge each thread, a judge settles their splits, and every verdict comes with evidence and a drafted reply. Use when the user asks whether review comments on their PR are right, whether an author really fixed or answered their comment, or picks "Judge the comments" in cc-prs.
---

# CC threads

First read `../_shared/cc-cli.md` and follow it.

This skill asks one question per thread: **does the claim hold against the code?** A comment isn't right because a senior wrote it, and it isn't wrong because it's the user's PR. The sceptics never learn who anyone is, so don't tell them, and don't take sides in how you present the verdicts.

## 1. Find the PR

- If the user named one, use it: `<repo> #<n>`.
- Otherwise run `./cc prs --json` and offer the PRs whose `threads` field is set, as a choice question (see `cc-prs` for the format). `N to judge` means comments by others on the user's PR. `author replied` means replies to the user's comments on someone else's PR. If none is set, say nothing is waiting and stop.

## 2. Judge

Run `./cc prs judge <repo> <n> --json` in the background and follow it with `./cc watch`. Relay each thread as it starts and each verdict as it lands, plus stalls and errors.

- By default it judges what waits since the last run. Pass `--all` only when the user asks to re-judge everything.
- It checks out the PR head as review feature `pr-<repo>-<n>`, the same as `./cc prs checkout`. Afterwards, offer `./cc worktree remove pr-<repo>-<n>`.
- If it stops because a provider isn't logged in, say which one. Don't edit the threads council to drop a sceptic unless the user asks.
- `./cc prs threads <repo> <n>` shows what would be judged without calling any model.

## 3. Report

Group the verdicts by tag, with the most actionable first:

```
<repo> #<n> · <title>
<counts by verdict, and how many were split>

VALID · path:line · <thread url>
  <claim in one line>
  - <evidence>
  Draft reply: <reply>
REFUTED · ...
VALID · split (sceptic-claude VALID, sceptic-grok REFUTED) · ...
```

- **split**: the sceptics disagreed and the judge decided. Say so plainly. A split verdict deserves the user's own look, so show both sceptics' tags.
- **UNJUDGED**: no usable verdict. Give the log path and offer a re-run. Never guess a verdict.
- `VALID` on the user's PR: offer a fix as a separate step, through `cc-worktree` and a council or a normal edit. Don't start it unasked.
- `PUSHBACK-HOLDS`: the user's comment looks wrong. Say so directly, with the evidence.

## Rules

- Posting a reply, resolving a thread, approving or requesting changes is outward-facing. Do it only when the user asks, after showing the exact text, thread by thread or as one confirmed batch, then with `gh`.
- The draft replies are suggestions. Shorten or rephrase them when the user asks, but never strengthen a claim beyond its evidence.
- Only PRs of catalog repos (`./cc repo list`).

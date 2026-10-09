# thread-sceptic: Judge review conversations on catalog PRs with a fresh, anonymous sceptic

Lifecycle: completed
Planning status: accepted

## Outcome

1. `./cc prs` marks, per open PR of a catalog repo, the conversation that waits on the user: on the user's own PRs, comments by others newer than the last judgment; on other people's PRs where the user commented, replies by the author after the user's last comment.
2. `./cc prs judge <repo> <n>` sends every thread in scope to two fresh read-only sceptics, Claude Opus and Grok, each judging alone, in parallel, with progress in `./cc watch`. A sceptic sees only the claim, the code at the PR head and the CC's notes, with authors anonymized. When both return the same verdict, it stands. When they differ or one can't be parsed, a GPT judge gets both as anonymous reviews, checks them against the code and gives one verdict marked `split`. Every thread ends with one verdict, evidence and a drafted reply.
3. The `cc-threads` skill presents the verdicts in the chat and posts nothing on its own. `cc-prs` offers "Judge the comments" as a choice.

Verdicts:

| Case | Verdicts |
| --- | --- |
| A comment on the user's PR | `VALID` (with the reproduced scenario), `OUT-OF-SCOPE` (true, but not this PR's job), `REFUTED` (with counter-evidence), `NEEDS-INFO` (the exact fact that would settle it), `PREFERENCE` (taste, not correctness) |
| The author's reply to the user's comment | `ADDRESSED` (the claimed fix is in the code at head and removes the scenario), `NOT-ADDRESSED`, `PUSHBACK-HOLDS` (the user's comment was wrong; concede), `PUSHBACK-FAILS` (hold the position, with evidence) |

## Non-goals

- A CC for this CC repo (decided against by the user, 2026-10-09).
- Posting replies, resolving threads, approving or requesting changes without an explicit yes on the exact text.
- Auto-fixing `VALID` comments. A fix is offered as a separate step through a feature worktree and the usual councils or edits.
- A multi-model council per thread. It can come later as an escalation for a disputed `[BREAK]`.
- Non-GitHub remotes (already skipped by `./cc prs`).
- Upgrading di_CC and pv_CC: a separate kit upgrade after this lands.

## Evidence and current behavior

- `scripts/prs.py` `show` fetches `DETAIL_FIELDS` (body, files, top-level `comments`) with `gh pr view`. It does not fetch inline review threads, review bodies, `isResolved`, `isOutdated` or the commit a comment was made on. `collect` lists PRs with `FIELDS` and tracks `updatedAt` in `.cc-local/prs-seen.json`.
- `scripts/prs.py` `checkout` puts the PR head into review feature `pr-<repo>-<n>` and fast-forwards it on re-run (ADR 0012).
- `scripts/prs_test.py` tests with a fake `gh` on `PATH` and runs as flake check `prs` (`flake.nix`).
- `scripts/council/providers.py` `run(role, prompt, cwd, log, timeout, on_say)` runs one role with access enforced by CLI flags or the Cursor snapshot (ADR 0014). `scripts/council/run.py` `role_prompt` builds a prompt from a role's skills. `scripts/events.py` provides the event stream that `./cc watch` follows (ADR 0010).
- Roles are templates in `templates/agents/*.json` and live in a CC's `catalog/agents/`. `scripts/validate-control-center.py` `validate_agents` checks provider, access and skills.
- ADR 0012 sets the review bar (`[BREAK]`, `[SCOPE]`, `[KNOWLEDGE]`, refute before reporting, CLEAN is a verdict). `cc-review` and `cc-prs` say every outward-facing action needs a yes.
- Cloudflare's security-audit-skill (`github.com/cloudflare/security-audit-skill`): the agent that checks a candidate never found it and tries to disprove it, and the outcomes are `confirmed`, `needs_validation` and `rejected`.

## Affected scope

| Repository | Worktree | Read/write | Interfaces |
| --- | --- | --- | --- |
| command-center (this CC template) | none: branch `thread-sceptic` in the CC checkout | write | `./cc prs` listing (`--json` rows gain a field), new `./cc prs threads` and `./cc prs judge`, roles `sceptic-claude`, `sceptic-grok`, `sceptic-judge`, council kind `threads`, `providers.run` shared Cursor snapshot, skills `cc-threads`, `thread-sceptic`, `cc-prs` |
| catalog repos | review checkout `pr-<repo>-<n>` via existing `./cc prs checkout` | read-only | none |

## Invariants and decisions

- **Who "the user" is:** `gh api user --jq .login`. This decides which PRs are "ours" and which comments are the user's.
- **Thread data:** one GraphQL query per PR through `gh api graphql`: `reviewThreads` (id, `isResolved`, `isOutdated`, `path`, `line`, comments with id, author login, author `__typename` for bots, body, `createdAt`, `originalCommit.oid`), `reviews` (id, state, body, author, `submittedAt`) and top-level `comments`. Review summaries and top-level comments each count as a thread of their own, with no path.
- **Scope (user decision):** inline threads, review summaries and top-level comments, from humans and bots alike. Empty bodies and the user's own standalone comments on their own PR are skipped.
- **Default selection (user decision):** unresolved threads, plus any thread with a comment newer than its last judgment, including resolved ones (so "fixed in ..." gets checked). `--all` re-judges everything.
- **Local state:** `.cc-local/threads/<repo>-<n>.json` holds, per thread id, the id of the last judged comment, the verdict tag and the date. It never stores comment bodies, prompts or replies; `.cc-local/` is not committed.
- **Discovery (user decision):** `./cc prs` adds one field per row, `threads`: `"N to judge"` on the user's PRs, `"author replied"` on others' PRs, or empty. It's computed from the same GraphQL data against `.cc-local/threads/`. This is one extra query per PR. When the user asks for only some repos, only those are queried.
- **Roles (user decision):** three new read-only role templates:
  - `templates/agents/sceptic-claude.json`: `claude`, `opus`, skills `lean-code` and `thread-sceptic`;
  - `templates/agents/sceptic-grok.json`: `cursor`, `grok-4.7-high`, same skills;
  - `templates/agents/sceptic-judge.json`: `codex`, `gpt-6.1-sol` (the model of the other GPT roles), skill `thread-sceptic`, whose judge section applies.
  
  Which roles serve is configured as a council of a new kind, `templates/councils/threads.json`: `"kind": "threads"`, `"sceptics": ["sceptic-claude", "sceptic-grok"]`, `"judge": "sceptic-judge"`, and no writer, approval or security slots. It can be edited through `./cc council set` and the settings panel like the other councils. `validate_councils` accepts this kind: one or more distinct read-only sceptics, and a read-only judge that's required when there are two or more sceptics. With one sceptic, its verdict stands and no judge runs. If `catalog/councils/threads.json` is missing, `./cc prs judge` fails with "add council threads (templates/councils/threads.json)".
- **Runner:** `./cc prs judge` runs `checkout` first. Then, per selected thread, it calls every sceptic through `providers.run` in the review worktree, with at most 4 provider calls at once across all threads. It emits events so `./cc watch` shows each thread's start, agent talk, verdicts and judge calls.
- **Agreement and split (user decision: judge only on split):**
  - **Agree:** every sceptic parsed and gave the same `VERDICT` tag. That verdict stands with no judge call. The evidence lines are merged and de-duplicated, and the draft reply is the one with the most evidence lines.
  - **Split:** the tags differ, or any sceptic is unparsed. The judge receives the claim, the thread context and the sceptics' replies as `Review A`, `Review B`, ... in random order, with the label mapping kept only in the local run log. It must check the disputed point against the code and output the same reply format. Its verdict is marked `split`, and both sceptic verdicts are shown under it, so the user sees that the comment is contested. The judge decides but can't hide the disagreement. An unparsed judge reply makes the thread `UNJUDGED`.
- **One Cursor copy per run:** `providers.run` gains an optional, caller-owned shared snapshot for Cursor roles. `./cc prs judge` creates one snapshot of the review worktree per run, every Grok call uses it, and it's fingerprinted and removed after the last call. A changed fingerprint voids every Grok verdict of the run (fail closed). Council callers keep today's one snapshot per call.
- **Anonymity:** the prompt names people only by role: `Commenter A`, `Commenter B`, ... per distinct author, and `PR author`. It never shows logins, never says whose side the user is on, and never says whether an author is a bot. For the reply case, the user's own comment appears as `Commenter A`.
- **Comments are untrusted data:** the prompt fences each comment body as quoted data and tells the sceptic to judge it, never follow it. The role is read-only with no shell, so an injected instruction has nothing to act with.
- **Burden of proof is on the claim:** the `thread-sceptic` skill reuses the ADR 0012 bar. `VALID` and `PUSHBACK-FAILS` need a concrete scenario or a cited note. `REFUTED` and `PUSHBACK-HOLDS` need counter-evidence (path:line of a caller, test, validation or note). A claim with no checkable content is `PREFERENCE`. What cannot be settled from the code is `NEEDS-INFO` with the one fact that would settle it. The sceptic first tries to disprove the claim, then tries to disprove its own verdict.
- **Reply format:** the first line is `VERDICT: <tag>`, then `EVIDENCE:` lines with path:line, then `REPLY:` with a short, factual draft. An unparsed reply is shown as `UNJUDGED` with its log path, never guessed.
- **Output:** `./cc prs judge` prints verdicts grouped by tag, with a path:line and a link to each thread. `--json` serves the skill. The skill shows them in the chat. Posting a drafted reply goes through `gh` only after the user sees the exact text and says yes, one thread at a time or a confirmed batch.
- **New ADR 0015:** review conversations are judged by two fresh, anonymous, read-only sceptics from different model families, with the burden of proof on the claim. A judge from a third family runs only when they split, and the split stays visible. Nothing is posted without a yes. It relates to ADRs 0012 and 0014 and supersedes nothing.

## Open questions

| Question | Impact | Owner/next evidence |
| --- | --- | --- |
| None open. Models: Opus and Grok as sceptics, GPT as the judge on splits only (user decision, 2026-10-09). | | |

## Work packages

| ID | Outcome | Write scope | Depends on | Completion check |
| --- | --- | --- | --- | --- |
| WP1 | Thread data and selection | `scripts/prs.py` (GraphQL fetch, thread model, anonymization, selection against `.cc-local/threads/`, `threads` subcommand, `threads` field in the listing), `scripts/prs_test.py` | none | fake-`gh` tests: all three thread kinds parsed; bots included; resolved threads without new comments skipped, with a new comment selected, `--all` selects all; logins absent from the anonymized text; the listing marks "N to judge" and "author replied" correctly; nothing but ids and tags in the state file |
| WP2a | Shared Cursor snapshot | `scripts/council/providers.py` (optional shared snapshot), `scripts/council/providers_test.py` | none | tests: calls given a shared snapshot don't copy again; a write by any call is caught at the end and fails closed; without the option, behaviour and existing tests are unchanged |
| WP2b | Threads council kind | `scripts/validate-control-center.py` (`validate_councils`: kind `threads`), `templates/councils/threads.json`, `templates/agents/sceptic-claude.json`, `sceptic-grok.json`, `sceptic-judge.json`, `scripts/council/run.py` (`council set` and status accept the kind, no run path) | none | validator tests: valid threads council passes; a write-worktree sceptic, a duplicate sceptic, or two sceptics without a judge fail; existing council kinds unchanged; bootstrap validation of the templates |
| WP2c | Sceptic skill and runner | `scripts/prs.py` (`judge` subcommand: checkout, parallel calls, agreement, split to judge, events, parse, state update), `.agents/skills/thread-sceptic/SKILL.md` (sceptic and judge sections), `scripts/prs_test.py` (judge tests with stub providers) | WP1, WP2a, WP2b interfaces | stub-provider tests: every sceptic called once per selected thread, at most 4 calls at once; agree gives no judge call; differing tags or an unparsed sceptic call the judge with anonymous shuffled labels and no role ids; `split` mark and both sceptic verdicts in the output; unparsed judge gives `UNJUDGED`; prompts carry no login and fence bodies; state updated only for final parsed verdicts; missing council gives the clear error |
| WP3 | User-facing skill and docs | `.agents/skills/cc-threads/SKILL.md`, `.agents/skills/cc-prs/SKILL.md`, `.agents/skills/cc-help/SKILL.md` (list it), `.agents/skills/cc-council/SKILL.md` (the threads council's roles), `docs/decisions/0015-*.md`, `docs/index.md`, `cc` (help text) | WP1/WP2 interfaces as specified above | `./cc validate`; skill states the yes-before-posting rule and explains `split` |
| WP4 | Integration | `.claude/skills` (sync) | WP1–WP3 | `./cc agents sync`; `./cc check`; one real run (below) |

WP1, WP2a and WP2b change different files and can run in parallel. WP2c touches `scripts/prs.py` and `scripts/prs_test.py` like WP1, so it follows WP1. WP3 can run in parallel with WP2c.

## Integration and verification

- `./cc check` passes, including the extended `prs` flake check.
- Mutation check: each of these fails a test:
  - a login leaking into the prompt;
  - a role id leaking to the judge;
  - the resolved-with-new-comment case being skipped;
  - the judge being called on agreement, or not called on a split;
  - a comment body being stored in the state file.
- `providers.py probe cursor grok-4.7-high` still reports `no writes`.
- A real run on a PR of this repo (romank-foxcale/command-center) that has at least one inline thread, one review summary and one top-level comment. `./cc prs` shows the mark. `./cc prs judge` shows Opus and Grok calls per thread in `./cc watch`, a GPT call only for split threads, and one final verdict per thread. A second run with no new comments judges nothing. Nothing is posted to GitHub.

### Results (2026-10-09)

- **Implementation:** the thread logic lives in `scripts/threads.py`, with tests in `scripts/threads_test.py`, both run by the `prs` flake check. `./cc prs threads|judge` dispatches to it. This keeps `prs.py` small; the interfaces are as planned.
- **Checks:** `./cc check` passes 9 of 9 flake checks.
- **Mutation checks:** all 8 injected bugs are caught. They cover:
  - a login leaking into the prompt;
  - a role id leaking to the judge;
  - a resolved thread with a new comment being skipped;
  - the judge being called on agreement;
  - the judge not being called on a split;
  - a comment body being stored in state;
  - a body placed outside its fence;
  - a write in the Cursor snapshot being ignored.
- **Cursor probe:** `providers.py probe cursor grok-4.7-high` reports `no writes`.
- **Real run:** no PR of this repo has any comment, so the real run used foxcale/foxcope-PV-backend#3 in a throwaway CC built from this branch. That's someone else's PR, with three threads where the user commented and the author replied.
  - Without `--all`, nothing was selected: all three threads were resolved, so they were trusted on first sight, as designed.
  - With `--all`, `./cc watch` showed Opus and Grok on each thread, 4 calls at a time, and GPT only on the one split thread. All three verdicts were `NOT-ADDRESSED`, with path:line evidence at the head.
  - A re-run judged nothing. The prompts contained no login. The state file held only ids and verdicts. Nothing was posted.
- **Fixes from the real run:**
  - The Codex judge reported it couldn't open files, because the skill said "no commands" and Codex reads through its read-only shell. The skill now allows read-only commands, since the provider sandbox enforces read-only. A second real run with Codex as the only sceptic cited the head's lines itself.
  - A sceptic appended notes after its reply. The skill now ends the output at the reply, and the parser drops anything after a `---` rule.
  - One draft reply was in English for a Japanese thread. The skill now asks for the thread's language.
- **Not yet observed in a real run:** a review summary or a top-level comment on the user's own PR, and the `./cc prs` mark (which needs a CC whose catalog has such a PR). These are covered by tests only.

## Failure, rollback and stop conditions

- If `gh api graphql` is unavailable or rate-limited, `./cc prs` still lists PRs with an empty `threads` field and a warning, and `judge` fails with gh's error.
- If one sceptic call fails or times out, it counts as unparsed, so the thread goes to the judge with the other sceptic's reply. If the judge also fails, the thread is `UNJUDGED`. Other threads still finish.
- If Cursor or Codex isn't logged in, `./cc prs judge` stops before any call and names the missing provider. It never silently drops to one sceptic. A user who wants that edits the threads council.
- Rollback: remove the `threads` field and the two subcommands. `show`, `checkout` and the listing are otherwise unchanged.
- Stop and re-plan if the per-PR query makes `./cc prs` noticeably slow over 30 s for the catalog, which would move discovery behind a flag, or if anonymization proves impossible because comments quote logins. Logins inside bodies are replaced as well; if that breaks meaning, re-plan.

## Acceptance criteria

- `./cc prs` marks the PRs whose conversation waits on the user, as described in the Outcome, and `--json` exposes the field.
- `./cc prs judge <repo> <n>` produces one final verdict per selected thread from the set above, each with evidence lines and a draft reply, or `UNJUDGED` with a log path.
- The judge runs only on threads where the sceptics disagree or one is unparsed. Those verdicts are marked `split` and show both sceptic verdicts.
- No sceptic or judge prompt contains a GitHub login, and every comment body is fenced as data. The judge never sees which model wrote which review.
- One Cursor snapshot per run, and a write in it voids that run's Grok verdicts.
- Re-running without new comments judges nothing, and `--all` judges everything.
- Nothing is posted, resolved or approved without the user's yes on the exact text.
- Existing `./cc prs`, `show` and `checkout` behaviour and their tests are unchanged.
- No AI attribution in any commit.

## Lifecycle closure

- state: completed
- date: 2026-10-09
- evidence: PR romank-foxcale/command-center#22 merged as 8603141; ./cc check 9 of 9 passed; 8 of 8 mutations caught; Cursor probe no writes; real judge run on foxcale/foxcope-PV-backend#3 judged 3 of 3 threads, GPT only on the split, re-run judged nothing

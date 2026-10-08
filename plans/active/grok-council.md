# grok-council: Cursor provider for Grok roles, and a three-model security review summarized by the judge

Lifecycle: active
Planning status: accepted

## Outcome

1. A council role can use `provider: cursor` (the user's Cursor subscription through the `cursor-agent` CLI) with any model Cursor lists; the settings model picker shows Cursor's models when it is logged in. The judge role uses a Grok model.
2. The security step of a council runs three independent read-only reviewers (Claude, GPT through Codex, Grok through Cursor) in parallel on the final diff; the judge receives their reviews anonymously, verifies each finding against the code and writes one summarized review whose `SEVERITY` line gates the run.

## Non-goals

- Research tasks or a research role: later work. The Cursor adapter is generic, so a future research role only needs a role file.
- Cursor roles with `write-worktree` access: the write path is not designed or probed; the validator rejects it.
- Restricting Cursor to Grok models in code: which model a role uses is configuration.
- Installing `cursor-agent` from `install/` or `./cc doctor` fixing it: doctor only reports it.
- Upgrading di_CC and pv_CC: a separate kit upgrade after this lands.
- Changing proposers, the writer or the testing council's lack of a security step.

## Evidence and current behavior

- Providers are fixed to `claude` and `codex` in `scripts/council/providers.py` (`PROVIDERS`, `login_status`, `models`, `command`, event parsing) and `scripts/validate-control-center.py` (`PROVIDERS`); `scripts/settings/state.py` detects tools `nix, git, claude, codex`; the settings picker lists `providers.py models` output, so a new provider appears there once the adapter lists models.
- The security step is one role: council field `security` holds one role id or `null` (`templates/councils/*.json`); `run.py` `write_and_verify` calls it once and blocks on `SEVERITY: high` or an unparsed reply. `scripts/council/progress.py` has one `security` step.
- `templates/agents/security.json` is Claude Opus, read-only, skill `council-security`; `judge.json` is Claude Opus with `council-judge`, which handles proposals only.
- ADR 0007 requires access to be enforced by CLI flags, never prompt text, and names "councils for security review are needed" as its revisit trigger.
- `cursor-agent` 2026.09.28 is installed in WSL and logged in (team "foxcale dev team"). It has `-p/--print`, `--output-format stream-json`, `--model`, `--mode plan|ask`, `--trust`, `--workspace`, `models` and `status`.
- Probes in throwaway folders with `grok-4.7-medium-fast`, 2026-10-08:
  - default `--print`: the edit tool wrote both files; the shell tool was rejected (no `--force`).
  - `--mode plan` and `--mode ask`: nothing written, but no tool call was attempted, so this does not prove enforcement.
  - `.cursor/cli.json` with `{"permissions":{"allow":["Read(**)"],"deny":["Write(**)","Shell(*)"]}}` in the workspace: the model called both tools; the CLI returned `writePermissionDenied ... Blocked by permissions configuration` and `Command blocked by permissions configuration`; nothing was written. This is tool-layer enforcement.
- Cursor lists Grok models (`grok-4.7-low|medium|high|xhigh` with `-fast` variants, `cursor-grok-4.6-*`, `cursor-grok-4.5-*`); none is marked "NO ZDR" (some Claude models through Cursor are).

## Affected scope

| Repository | Worktree | Read/write | Interfaces |
| --- | --- | --- | --- |
| command-center (this CC template) | none: branch `grok-council` in the CC checkout | write | `providers.py` provider API, role and council JSON schema, `./cc council`, settings panel, `council-judge` and `council-security` skills |
| sibling project repos | none | none: Cursor roles read a snapshot, never the worktree | none |

## Invariants and decisions

- Provider id `cursor`, binary `cursor-agent`. Login: `cursor-agent status` (a line starting with the check mark and "Logged in"); models: `cursor-agent models`, ids before ` - `.
- Cursor access is enforced by Cursor's permission configuration, not by prompt or mode: a Cursor role runs with `--workspace <snapshot> --trust --print --output-format stream-json --model <model>`, without `--force`, where `<snapshot>` is a fresh temporary copy of the files Git would commit in the feature worktree (tracked and untracked, never ignored) plus the CC's own `.cursor/cli.json` that allows `Read(**)` and denies `Write(**)` and `Shell(*)`. A project's own `.cursor/cli.json` in the copy is replaced. The snapshot is deleted after the call.
- The validator rejects `provider: cursor` with `access: write-worktree`.
- `providers.py probe cursor <model>` must report `no writes` before the change is called done; the probe uses the same snapshot path as a real run.
- Council field `security` accepts a list of role ids (`[]`/`null` = no security step) or, for existing catalogs, one role id. Templates: `security-claude` (Claude Opus), `security-gpt` (Codex, same model as the other GPT roles), `security-grok` (Cursor, Grok); `security.json` is replaced by `security-claude.json`.
- Security reviewers run in parallel, each read-only, with the existing `council-security` skill; their replies are saved as `review-<role>.md`.
- With two or more reviewers, the judge gets the diff and the reviews as anonymous `Review A`, `Review B`, ... (shuffled, mapping in `state.json`), and a new section of `council-judge` for security summaries: verify each finding against the code, merge duplicates, drop what does not hold with the reason, and output `SEVERITY:` first, then the confirmed findings. Saved as `security.md`. With one reviewer, its reply is `security.md` as today.
- The gate (user decision, Q1): the run finishes `blocked-security` when the judge's summary says `SEVERITY: high` or is unparsed, **or** any single reviewer says `high` or is unparsed. The judge never overrules a reviewer's high finding; its assessment of that finding goes into `security.md`, and the user decides. Otherwise the judge's severity is the recorded `security` value.
- Grok model (user decision, Q2): `grok-4.7-high` for `judge.json` (moves to `provider: cursor`) and `security-grok.json`. The judge's other duties (proposals, diagnoses, test sets) are unchanged.
- A new ADR records Cursor as a read-only provider enforced by a permission-config snapshot, and the multi-reviewer security step; it supersedes the "Access is enforced by CLI flags" bullet of ADR 0007 by widening it to "CLI flags or provider permission config, never prompt text".

## Open questions

| Question | Impact | Owner/next evidence |
| --- | --- | --- |
| None open. | | |

## Work packages

| ID | Outcome | Write scope | Depends on | Completion check |
| --- | --- | --- | --- | --- |
| WP1 | Cursor provider with snapshot enforcement | `scripts/council/providers.py`, a new `scripts/council/providers_test.py`, `scripts/validate-control-center.py` (`PROVIDERS`, cursor read-only rule), `scripts/settings/state.py` (tool detection) | none | unit tests for command line, login and model parsing, snapshot contents and cleanup; `providers.py probe cursor <grok model>` prints `no writes` |
| WP2 | Multi-reviewer security step and judge summary | `scripts/council/run.py`, `scripts/council/progress.py`, `scripts/validate-control-center.py` (`security` list), `.agents/skills/council-judge/SKILL.md` | none (interface: council JSON above) | a council test with stub providers: three reviews in parallel, anonymous labels, the gate (judge high, any reviewer high, unparsed), single-reviewer and `null` unchanged |
| WP3 | Templates, skill text, ADR | `templates/agents/*.json`, `templates/councils/*.json`, `docs/decisions/0014-*.md`, `docs/decisions/0007-agent-councils.md`, `docs/index.md`, `.agents/skills/cc-council/SKILL.md` | WP1, WP2 interfaces | `./cc validate`, bootstrap validation of the templates |
| WP4 | Integration | `.claude/skills` (sync) | WP1–WP3 | `./cc agents sync`, `./cc check`; one real coding council run on a scratch feature with Grok judge and three security reviewers |

WP1 and WP2 change different files except `validate-control-center.py`; WP1 owns `PROVIDERS` and the cursor rule, WP2 owns the `security` field check, in separate functions.

## Integration and verification

- `./cc check` passes, including the new provider tests and the council test.
- `providers.py probe cursor <judge model>` reports `no writes`.
- A real run on a scratch feature: `./cc council run` reaches the security step, shows three reviewer calls and a judge summary in `./cc watch`, and the gate blocks on a reviewer high even when the judge says lower.

### Results (2026-10-08)

- `./cc check`: 9 of 9 flake checks pass, including the new `council` check (`providers_test.py`, `council_test.py`). Mutation checks: six injected bugs in the Cursor adapter and five in the security step (including reviewer names leaking to the judge) each fail a test.
- `providers.py probe cursor grok-4.7-high`: `no writes`. A logged run showed Grok reading a file, then two edits and one shell command, each refused by the CLI ("Write permission denied", "Command blocked by permissions configuration").
- Real end-to-end run of the security step: the template repo has no catalog or feature, so instead of `./cc council run` the real `Run.review_security` ran with the template roles on a scratch Git repo whose diff added `subprocess.run(f'tar czf out.tgz {name}', shell=True)`. Claude Opus, Codex `gpt-6.1-sol` and Cursor `grok-4.7-high` reviewed in parallel (13 s, 14 s, 25 s), all rated it `high`; the Grok judge (1 min 48 s) received anonymous reviews A, B and C, confirmed the injection, merged duplicates and credited reviews by label; the run blocked with "the security summary says high"; the scratch worktree was unchanged.
- Settings show Cursor's 256 models once logged in (`providers.py models`).

## Failure, rollback and stop conditions

- If a `cursor-agent` update stops honouring `.cursor/cli.json` in `--print` mode, the probe fails and the provider must refuse to run (fail closed), never fall back to prompt-only restriction.
- Rollback: point `judge.json` and the councils back to Claude roles; the code paths for one reviewer and Claude/Codex stay.
- Stop and re-plan if the snapshot copy of a real worktree is too slow (over 30 s) or too large to be practical.

## Acceptance criteria

- A role with `provider: cursor` and `access: read-only` runs; with `write-worktree` the catalog fails validation.
- The Cursor probe writes nothing; a unit test proves the deny config is present in every snapshot and that a project's own `.cursor/cli.json` is replaced.
- The settings model picker lists Cursor models when logged in.
- A coding council with three security reviewers produces `review-<role>.md` for each, an anonymous judge summary in `security.md`, and blocks when the judge or any reviewer says high or is unparsed.
- Catalogs with `"security": "<one role>"` or `null` behave exactly as before.
- No AI attribution in any commit.

## Lifecycle closure

Not closed.

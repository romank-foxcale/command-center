# agent-councils: Configurable multi-model agent roles and coding/testing councils run by ./cc council

Lifecycle: completed
Planning status: accepted

## Outcome

A CC user assigns a provider and model to each agent role in config, and runs a coding council and a testing council against a feature worktree with one command. Claude and GPT each propose independently, an anonymous judge decides, the user approves, a writer implements with maximum reuse, and the result counts only when `./cc feature <feature> verify` passes.

## Non-goals

- Recreating Paperclip: no long-running agents, message bus, org chart or dashboard. A council is a fixed pipeline of headless CLI calls.
- Storing or handling credentials. Each provider CLI keeps its own login.
- Pay-per-token API keys. Only subscription logins via the `claude` and `codex` CLIs.
- Committing, pushing or opening PRs from a council. The user commits.
- Councils for planning or security (security runs as a single read-only reviewer step).

## Evidence and current behavior

- No council, judge, role or model configuration exists in the CC (repository search for council, judge, model and subagent finds none).
- `GUIDE.md` states the CC "never picks a model"; this plan reverses that part and keeps "holds no credentials".
- The reuse-first coding rule existed only in the removed personal `fox-code` skill; the CC has none.
- `grill-task-planning` already produces work packages with an exact write scope and a completion check; councils consume them.
- `claude` 2.1.287 is installed in WSL and logged in through claude.ai (`claude auth status`).
- The `codex` CLI is not installed on Windows or in WSL; `install/install.sh --tools codex` can install it.
- `./cc feature <feature> verify` (ADR 0006) is the existing definition of working code, including target platform gates.

## Affected scope

| Repository | Worktree | Read/write | Interfaces |
| --- | --- | --- | --- |
| command-center (this CC template) | none: branch `agent-councils` in the CC checkout | write | `./cc council`, `./cc doctor`, `catalog/agents`, `catalog/councils`, skills, validators |
| sibling project repos | `../worktrees/<feature>/<repo>_wt` at run time | the writer step only | none changed by this plan |

## Invariants and decisions

- Roles live in `catalog/agents/<role>.json`: `provider` (`claude` or `codex`), `model`, `access` (`read-only` or `write-worktree`), `skills`. Councils live in `catalog/councils/<name>.json` as an ordered list of stages that reference roles. Defaults ship with the template; users edit the JSON or ask the `cc-council` skill.
- Default models: proposers Claude Opus and the best Codex model; judge Claude Opus; writer Claude Opus; security reviewer Claude, read-only.
- Restrictions are enforced by each CLI's own flags (Claude tool allowlist and permission mode; Codex `--sandbox read-only` or `workspace-write`), never by prompt text alone.
- Proposers, judge, test writers in the proposal stage, and security are read-only. Only the writer may edit, and only inside the feature worktree.
- The judge sees "Proposal A" and "Proposal B" in random order, never the provider or model. The mapping is revealed to the user after the verdict.
- A run pauses after the verdict: `./cc council approve <run-id> [--pick A|B] [--note <text>]` resumes it. A config switch `approval: false` disables the pause per council.
- Coding council: propose (Claude and GPT in parallel) → judge (pick or hybrid) → user approval → write (reuse-first) → `./cc feature <feature> verify` → on failure, the writer retries with the failure output, at most 2 times → security review of the final diff.
- Testing council: both models write tests independently in isolated copies → judge merges them into one test set → user approval → writer applies → verify. A new test that fails against the implementation is reported as a suspected bug; the code is never changed and tests are never weakened by this council.
- Security findings of high severity stop the run before it is reported as done; the council does not fix them automatically.
- Role skills are injected into each CLI call's prompt by the runner, because the CLI runs in the project worktree where the CC's skills are not discovered.
- Run artifacts (proposals, verdict, diffs, logs) live in `../worktrees/<feature>/.cc-runs/<run-id>/`, outside every Git repository. Full conversations and reasoning are not stored.
- `./cc doctor` lists each provider as logged in or not. A role whose provider is logged out fails the run; there is no silent fallback to another provider or model.
- No AI attribution anywhere (AGENTS.md hard rule).

## Open questions

| Question | Impact | Owner/next evidence |
| --- | --- | --- |
| Codex CLI installed and logged in with the user's ChatGPT plan | Blocks every GPT step | User runs `codex login` in WSL; `codex login status` |
| Exact current `codex exec` flags and model ids on the user's plan | Adapter flags in WP2 | `codex exec --help` after install |
| Subscription rate limits under parallel council calls | Runs may stall or fail | Observe in the WP7 end-to-end run; add a clear error, not retries that hide it |

## Work packages

| ID | Outcome | Write scope | Depends on | Completion check |
| --- | --- | --- | --- | --- |
| WP1 | Role and council schemas, default configs and validation | `templates/agents/`, `templates/councils/`, `scripts/materialize-template.py`, `scripts/validate-control-center.py` | none | A broken role or council config fails `./cc bootstrap validate` with a precise message; defaults validate |
| WP2 | Provider adapters (claude, codex) mapping access levels to CLI flags; login checks in `./cc doctor` | `scripts/council/providers.py`, `cc` (doctor) | none | A read-only role cannot write in a test directory for both providers; doctor reports both login states |
| WP3 | Role skills: propose, judge, code-write (reuse ladder), test-write, security-review | `.agents/skills/council-*` | none | `./cc agents check` and knowledge validation pass |
| WP4 | Coding council runner with approval pause, retries and run artifacts | `scripts/council/run.py`, `cc` (council) | WP1, WP2, WP3 | Fixture run: two proposals, anonymous verdict, pause, approve, write, verify, security report |
| WP5 | Testing council | `scripts/council/run.py`, `templates/councils/testing.json` | WP4 | Fixture run produces one merged test set; a failing new test is reported, code untouched |
| WP6 | `cc-council` skill (start, approve, status, change a role's model) and OpenCode permissions | `.agents/skills/cc-council/`, `opencode.json` | WP4 | Skill synced; `./cc check` passes |
| WP7 | ADR 0007, GUIDE and README updates; end-to-end run with real Claude and GPT | `docs/`, `GUIDE.md`, `README.md` | WP5, WP6 | E2E coding and testing council on a fixture repo with both providers |

WP1, WP2 and WP3 can run in parallel; they share no files.

## Integration and verification

- `./cc check` and `./cc validate` after every package.
- WP7 end-to-end run in a throwaway CC with a small fixture repo and both real providers, including one forced verify failure to exercise the retry limit.

## Failure, rollback and stop conditions

- Stop and report if a provider is logged out, a CLI flag no longer exists, or the sandbox cannot be enforced for a read-only role; never fall back to prompt-only restrictions.
- After 2 failed writer retries, stop with the verify output; never edit tests or checks to pass.
- Rollback: the feature is additive; removing `./cc council` and the council skills restores current behaviour. Runs never touch the base clones.

## Acceptance criteria

- A user changes a role's model by editing one JSON field (or asking `cc-council`) and the next run uses it, as visible in the run log.
- `./cc doctor` shows which of claude and codex are logged in.
- One command starts a coding council on a feature; both providers' proposals, the anonymous verdict and the provider mapping are in the run folder; the run waits for approval.
- After approval, the code is written only in the feature worktree, `./cc feature <feature> verify` passes or the run stops after 2 retries with the reason, and a security review is reported.
- The testing council produces one merged test set and never changes production code.
- No AI attribution appears in any file, commit or message the council produces.

## Lifecycle closure

- state: completed
- date: 2026-10-06
- evidence: E2E in a throwaway CC with Claude opus and Codex gpt-6.1-sol: coding council hybrid verdict, approval, write, feature verify pass, security none; testing council caught a planted multiply bug without touching code; judge rejected an unpassable task instead of faking the platform; stubbed writer stopped after 2 retries; read-only and worktree write limits probed for both CLIs

# runtime-flows: Agents can read how the code runs, from verified runtime flow notes

Lifecycle: completed
Planning status: accepted

## Outcome

Agents (interactive sessions and every council role) can read how a catalog project runs: the order of steps in its key flows (startup, a request's lifecycle, background jobs, config resolution) and, once repos interact, the flows across repos. Each step cites the project code it comes from, and the CC fails its checks when a cited file or symbol no longer exists, so a stale flow cannot silently mislead an agent.

## Non-goals

- Cross-repo smoke tests in `nix/workflows`: later, per project, once projects are runnable. A flow can already cite an existing workflow check as evidence.
- Migrating the user's real CC: a separate follow-up plan after this one is completed (decision 0003: template changes do not reach existing CCs).
- Generating flows automatically from static analysis or runtime traces.
- Detecting semantic drift by content hashes: an edited cited file is a review finding, not a check failure.
- Flows in `./cc prs judge` (thread sceptic) prompts.

## Evidence and current behavior

- Note evidence must be a path inside the CC repo; URLs are skipped and nothing can cite project code (`scripts/validate-knowledge.py`, `local_target`).
- Every project adapter exposes its pinned source as `src` (`nix/lib/default.nix`, `mkProject`), and `./cc feature <f> verify` overrides the flake inputs with the feature's worktrees (`scripts/verify.py`, `override_args`). A Nix check that reads `src` therefore sees exactly the code under test.
- The flake already passes per-adapter data to a check as a JSON file (`adapterTargetsFile` in `flake.nix`).
- Council prompts contain only role skills, the task and repo context; no knowledge notes (`scripts/council/run.py`, `role_prompt`).
- `cc-review` already reports `[KNOWLEDGE]` findings against notes (`.agents/skills/cc-review/SKILL.md`).
- The template has no projects and no workflows (`nix/projects/default.nix`, `nix/workflows/default.nix` are empty).
- The user's repos do not interact at runtime yet, so the first flows are single-repo.

## Affected scope

| Repository | Worktree | Read/write | Interfaces |
| --- | --- | --- | --- |
| this CC (template) | none: CC branch `runtime-flows` | write | note frontmatter `evidence`, `validate-knowledge.py` CLI, knowledge flake check, council role prompt, `cc-review` and new `cc-flow` skills |

No catalog repository changes.

## Invariants and decisions

- **Flow note:** one note per flow in `docs/flows/<flow>.md`, from `templates/flow.md`: purpose, a Mermaid `sequenceDiagram`, numbered steps each citing evidence, and the contracts between repos when there are several. At most 220 lines, like every note. Explains order and reasons; never restates code or build commands.
- **Repo evidence format:** `repo:<id>/<path>#<symbol>` in a note's `evidence` list. `<id>` is a catalog repository of kind `project` with an adapter; `<path>` is relative to the repo root; `#<symbol>` is optional plain text that must appear in the file (a function, class, route, config key). Line numbers are never used.
- **Drift rule (agreed):** the knowledge check fails when a cited repo is unknown, is a reference repo, has no adapter, or when the cited file or symbol is missing from the pinned or feature source. When a PR merely edits a cited file, `cc-review` raises a `[KNOWLEDGE]` finding asking to re-verify the flow. No content hashes.
- **Source resolution:** in Nix, the knowledge check gets a JSON map from catalog id to adapter `src`. Outside Nix (`./cc validate`, the Python fallback), `repos/project/<id>` is used.
- **Councils:** the runner adds every `active` flow note that cites the council's repository to every role's prompt, in full, under `# Runtime flows`. Which flows apply is derived from the cited repo ids, never from a second list.
- **Long-lived decisions:** a new ADR `0017-runtime-flows` (the flow kind, the repo evidence format, the drift rule) and a glossary term `runtime flow` distinguishing it from `nix/workflows` (build pipelines). `0007-agent-councils` gains a relation and one line on flows in briefs.

## Open questions

| Question | Impact | Owner/next evidence |
| --- | --- | --- |
| Repos without an adapter cannot be cited, so flows wait for onboarding | Flows in the user's CC may wait until its repos are `adapted` | User, at migration planning |
| A symbol is matched as plain text, so a comment can satisfy it | A removed function whose name survives in a comment is not caught | Accepted; revisit if it misleads in practice |
| Many flows for one repo make council prompts long | Token cost per call | Revisit when a repo has more than 5 active flows; the token measurement shows the cost |

## Work packages

| ID | Outcome | Write scope | Depends on | Completion check |
| --- | --- | --- | --- | --- |
| WP1 | The flow note kind is defined and linked into the knowledge map | `docs/decisions/0017-runtime-flows.md`, `docs/glossary/runtime-flow.md`, `docs/glossary/index.md`, `docs/flows/index.md`, `templates/flow.md`, `docs/index.md`, `docs/rules/knowledge-layout.md`, `docs/decisions/0007-agent-councils.md` | none | `python3 scripts/validate-knowledge.py .` passes |
| WP2 | The knowledge check verifies repo evidence against pinned or feature sources | `scripts/validate-knowledge.py`, `scripts/validate_knowledge_test.py` (new), `flake.nix` (sources map for the knowledge check; run the new test) | none (format fixed above) | the new test passes: a valid single-repo flow passes; a missing file, a missing symbol, a reference repo, an unknown id and a repo without an adapter each fail with a message naming the note and the evidence; the same failure appears with a sources map pointing at a modified copy (feature override) |
| WP3 | Council roles receive the flows that cite their repository | `scripts/council/run.py`, `scripts/council/council_test.py` | none (format fixed above) | `council_test.py`: the role prompt contains the full text of active flows citing the run's repo, and none citing only other repos or with another status |
| WP4 | `cc-review` asks to re-verify a flow whose cited file a PR edits | `.agents/skills/cc-review/SKILL.md` | WP1 | the skill names the rule, its `[KNOWLEDGE]` wording and how to find affected flows |
| WP5 | `cc-flow` drafts, re-verifies and lists flows with user confirmation | `.agents/skills/cc-flow/SKILL.md` (new), `.agents/skills/cc-help/SKILL.md` if it lists skills statically | WP1, WP2 | the skill drafts from `repos/project/<id>` clones, asks the user to confirm every flow before writing it, re-verifies on a check failure or review finding, ends with `./cc validate` |

WP1, WP2 and WP3 can run in parallel; WP4 and WP5 follow WP1 (and WP5 also WP2).

## Integration and verification

Run `./cc agents sync`, then `./cc check` on the branch. No project code changes, so `./cc verify` gates no target platform.

## Failure, rollback and stop conditions

- Stop and revisit the design if the knowledge check cannot receive adapter sources without making `./cc check` fetch or build project code beyond what other checks already require.
- Rollback: revert the branch. Flow notes are additive; no existing note or check changes meaning.

## Acceptance criteria

1. A flow note citing `repo:<id>/<path>#<symbol>` passes `./cc check` when everything cited exists, and fails it with a message naming the note, the evidence and what is missing when a cited file or symbol is removed; the same holds under a feature override (WP2 test inside the knowledge check).
2. Citing a reference repo, an unknown id or a repo without an adapter fails the check.
3. Council role prompts contain exactly the active flows citing the run's repository (WP3 test).
4. `cc-flow` and the updated `cc-review` exist in `.agents/skills/` and are synced to `.claude/skills/`; ADR 0017 and the glossary term are linked from the knowledge map.
5. `./cc check` passes.

## Lifecycle closure

- state: completed
- date: 2026-10-11
- evidence: ./cc check passes 9 checks; scripts/validate_knowledge_test.py and scripts/council/council_test.py cover acceptance criteria 1-3; cc-flow and cc-review synced; ADR 0017 linked from docs/index.md

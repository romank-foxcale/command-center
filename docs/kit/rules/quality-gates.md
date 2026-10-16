---
id: kit.rules.quality-gates
title: Quality gates per stack
status: active
summary: Each repository declares its languages in the catalog; its adapter runs the stack's formatter, linter and architecture rules as ordinary checks and may expose a quality.mutation gate, which ./cc verify --quality runs and only warns about when it is missing.
verified_at: 2026-10-17
evidence:
  - scripts/repositories.py
  - scripts/verify.py
  - scripts/council/run.py
  - nix/lib/default.nix
  - flake.nix
  - templates/project.nix
  - templates/workflow.nix
relations:
  - docs/index.md
  - docs/kit/decisions/0008-quality-gates.md
  - docs/kit/rules/project-adapters.md
  - docs/kit/decisions/0006-target-platform-gates.md
  - docs/kit/decisions/0022-deterministic-checks-before-review.md
---

# Quality gates per stack

## Contract

- `catalog/repositories/<id>.json` has `stack`: the repository's languages (`java`, `python`, `typescript`, `csharp`, ...), set by `./cc repo add --stack` or `./cc repo set-stack`.
- The adapter may declare `quality.mutation` in `ccLib.mkProject`: a derivation (pure, whole repository) or an app (impure, may read `CC_WORKTREE` and `CC_BASE_REF` to mutate only the feature's changed lines).
- `./cc verify --quality` (and every council run) executes it after the target gates. A missing gate prints `WARN: no gate` and does not fail; a failing gate fails verification. Quality gates never run in `./cc check`, because mutation testing is slow.
- The gate must fail when a mutant survives. Several tools exit successfully regardless, so the adapter checks the tool's results itself.

## Default tools

Defaults for onboarding; an adapter may choose otherwise. Confirm the tool's current options when writing the first adapter for a stack.

| Stack | Static checks | Tests | Property-based | Mutation | Mark an equivalent mutant |
|---|---|---|---|---|---|
| Java | Spotless (`spotless:check`), PMD or Error Prone, ArchUnit tests | JUnit 5 | jqwik | PIT | exclude in the PIT configuration |
| Python | `ruff format --check`, `ruff check`, mypy or pyright, import-linter | pytest | Hypothesis | mutmut | `# pragma: no mutate` |
| JavaScript / TypeScript | Prettier `--check`, ESLint with typescript-eslint, `tsc --noEmit`, dependency-cruiser | Vitest or Jest | fast-check | StrykerJS | `// Stryker disable next-line <mutator>: <reason>` |
| C# / .NET | `dotnet format --verify-no-changes`, Roslyn analyzers as errors, NetArchTest | xUnit or NUnit | CsCheck or FsCheck | Stryker.NET | `// Stryker disable once <mutator>: <reason>` |
| Rust | `cargo fmt --check`, `cargo clippy -- -D warnings` | cargo test | proptest | cargo-mutants | `#[mutants::skip]` |
| C / C++ | `clang-format --dry-run --Werror`, clang-tidy | GoogleTest or Catch2 | RapidCheck | Mull | Mull's ignore configuration |

## Static checks

A formatter, linter or architecture rule decides the same way on every run, so whatever such a tool can check is left to it, not to a reviewer or a council.

- They are ordinary entries in the adapter's `checks` (for example `checks.lint`, `checks.architecture`), not a quality gate: they are fast, so they run in `./cc check` and every `./cc verify`, and a failure fails both.
- They run in check mode: they report and fail, never rewrite the sources.
- The repository's own configuration and pinned tool versions come first; the defaults above are proposed only where it has none. When an existing codebase has many violations, start from the tool's baseline or a small rule set that passes today, then tighten. Never disable a rule to make one change pass.
- Architecture rules (ArchUnit, import-linter, dependency-cruiser, NetArchTest) live in the repository as tests; the adapter runs them with the other tests or as their own check.
- A contract between repos (an API spec and the client generated from it) is a workflow check, not a project check: `ccLib.mkContractCheck`, starting from `templates/workflow.nix`.
- A review lesson with `route: gate` lands here: a linter rule or an architecture test inside one repo, or a contract check when it spans repos.

## Equivalent mutants

Some mutants cannot change behaviour (for example `<` to `<=` where both branches return the same value at the boundary), so no test can kill them. Mark each one with the tool's skip mechanism and a one-line reason in the code; never mark a mutant that a test could kill, and never weaken the gate's threshold instead.

## mutmut 3.2 (verified with the fixture)

- It mutates only code under `src/`, `lib/` or a directory named like the repository; `paths_to_mutate` is ignored.
- Tests run inside the `mutants/` copy, so the pytest configuration must be copied with `[mutmut] also_copy = setup.cfg`.
- pytest must be importable from mutmut's interpreter: `python3.withPackages (ps: [ ps.pytest (ps.toPythonModule pkgs.mutmut) ])`.
- `mutmut run` exits 0 with survivors; fail the gate on `mutmut results` lines ending in `survived`, `no tests`, `timeout` or `suspicious`.

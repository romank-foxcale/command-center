---
id: rules.quality-gates
title: Quality gates per stack
status: active
summary: Each repository declares its languages in the catalog and may expose a quality.mutation gate in its adapter; ./cc verify --quality runs it and only warns when it is missing.
verified_at: 2026-10-06
evidence:
  - scripts/repositories.py
  - scripts/verify.py
  - scripts/council/run.py
  - nix/lib/default.nix
  - flake.nix
relations:
  - docs/index.md
  - docs/decisions/0008-quality-gates.md
  - docs/rules/project-adapters.md
  - docs/decisions/0006-target-platform-gates.md
---

# Quality gates per stack

## Contract

- `catalog/repositories/<id>.json` has `stack`: the repository's languages (`java`, `python`, `typescript`, `csharp`, ...), set by `./cc repo add --stack` or `./cc repo set-stack`.
- The adapter may declare `quality.mutation` in `ccLib.mkProject`: a derivation (pure, whole repository) or an app (impure, may read `CC_WORKTREE` and `CC_BASE_REF` to mutate only the feature's changed lines).
- `./cc verify --quality` (and every council run) executes it after the target gates. A missing gate prints `WARN: no gate` and does not fail; a failing gate fails verification. Quality gates never run in `./cc check`, because mutation testing is slow.
- The gate must fail when a mutant survives. Several tools exit successfully regardless, so the adapter checks the tool's results itself.

## Default tools

Defaults for onboarding; an adapter may choose otherwise. Confirm the tool's current options when writing the first adapter for a stack.

| Stack | Tests | Property-based | Mutation | Mark an equivalent mutant |
|---|---|---|---|---|
| Java | JUnit 5 | jqwik | PIT | exclude in the PIT configuration |
| Python | pytest | Hypothesis | mutmut | `# pragma: no mutate` |
| JavaScript / TypeScript | Vitest or Jest | fast-check | StrykerJS | `// Stryker disable next-line <mutator>: <reason>` |
| C# / .NET | xUnit or NUnit | CsCheck or FsCheck | Stryker.NET | `// Stryker disable once <mutator>: <reason>` |
| Rust | cargo test | proptest | cargo-mutants | `#[mutants::skip]` |
| C / C++ | GoogleTest or Catch2 | RapidCheck | Mull | Mull's ignore configuration |

## Equivalent mutants

Some mutants cannot change behaviour (for example `<` to `<=` where both branches return the same value at the boundary), so no test can kill them. Mark each one with the tool's skip mechanism and a one-line reason in the code; never mark a mutant that a test could kill, and never weaken the gate's threshold instead.

## mutmut 3.2 (verified with the fixture)

- It mutates only code under `src/`, `lib/` or a directory named like the repository; `paths_to_mutate` is ignored.
- Tests run inside the `mutants/` copy, so the pytest configuration must be copied with `[mutmut] also_copy = setup.cfg`.
- pytest must be importable from mutmut's interpreter: `python3.withPackages (ps: [ ps.pytest (ps.toPythonModule pkgs.mutmut) ])`.
- `mutmut run` exits 0 with survivors; fail the gate on `mutmut results` lines ending in `survived`, `no tests`, `timeout` or `suspicious`.

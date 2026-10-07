---
name: debug
description: Find the root cause of a bug, test failure, build or verify failure, flaky test or unexpected behaviour before changing any code - reproduce on the right platform, trace backwards, test one hypothesis at a time, fix once at the source with a failing test first. Use for any failure, before proposing a fix, and again whenever a fix did not work.
---

# Debug

**No fix without a root cause.** A symptom fix is a failure, even when the error disappears. Investigating is faster than guess-and-check, also for "simple" bugs and also under time pressure.

Work through the four phases in order. A later phase never starts before the earlier one is done.

## 1. Investigate the root cause

1. **Read the whole error.** Every line of the stack trace, every warning before it, file paths, line numbers, exit codes. The answer is often already there.
2. **Reproduce it reliably.** Exact steps, exact command, every time. Reproduce through the CC first (`./cc feature <feature> verify <repo>` or the failing check from `./cc show`), on the platform where it fails: a Windows-only bug is reproduced through the Windows gate, not on Linux. Direct tool commands (`pytest -k`, `gradle test --tests`, `dotnet test --filter`) are fine for diagnosis; the fix still has to pass through the CC. Not reproducible yet: gather more data, do not guess.
3. **Check what changed.** `git log` and `git diff` against the last known good state, dependency and lock-file changes, configuration, environment, platform. When a good and a bad commit are known, `git bisect` with the failing command finds the culprit.
4. **Instrument component boundaries.** In a chain of components (CI → build → package, API → service → database), log what enters and leaves each boundary and whether configuration and environment arrive, run once, and let the evidence show where it breaks. Then investigate only that component.
5. **Trace backwards.** When the error surfaces deep in the call stack, follow the bad value up the callers until its origin; see `root-cause-tracing.md`.

## 2. Compare with what works

1. Find similar code in this codebase that works.
2. If you follow a reference implementation or documentation, read it completely; skimming guarantees a partial copy.
3. List every difference between working and broken, however small. Do not assume a difference "can't matter".
4. Note what the broken code depends on: configuration, environment, ordering, platform, versions.

## 3. One hypothesis at a time

1. Write it down: "X is the root cause because Y".
2. Test it with the smallest possible change or probe, one variable at a time.
3. Confirmed: go to phase 4. Refuted: form a new hypothesis from the new evidence; never stack another change on top of a failed one.
4. Stuck: say "I don't understand X", and research or ask. Never pretend.

## 4. Fix at the source

1. **Failing test first.** Reproduce the bug as the smallest automated test in the repository's test framework, and watch it fail for the right reason (`tdd`). A bug that cannot be tested automatically gets a one-off reproduction script used for diagnosis only, and the reason is reported.
2. **One fix, at the root cause.** No "while I'm here" changes, no bundled refactoring. When the root cause sits in a shared function, fix it there once for every caller (`lean-code`).
3. **Guard where it pays.** When bad data caused the bug, add validation where it enters the system and a guard at the dangerous operation it reached; see `defense-in-depth.md`.
4. **Verify.** The new test passes, the whole suite passes, and `./cc feature <feature> verify` passes on every target platform. Report any failure you saw, including ones you did not cause.
5. **Offer to record it.** When the fix is verified and the root cause took real investigation or needed a workaround, offer `cc-learn` in one line. Do not record anything without the user's yes.
6. **Fix did not work: stop.** Fewer than three attempts: return to phase 1 with the new evidence. **Three failed fixes: stop fixing.** When every fix exposes a new problem somewhere else, the design is wrong, not the hypothesis. Report what you learned and discuss the architecture with the user before attempting a fourth fix.

## Stop signals

Return to phase 1 when you catch yourself thinking: "quick fix now, investigate later"; "just try X and see"; "change several things, then run the tests"; "skip the test, I'll check by hand"; "it's probably X"; "I don't fully understand, but this might work"; "one more attempt" after two failures; or when you list fixes before tracing the data flow. The same applies when the user asks "is that actually happening?", says "stop guessing", or sounds stuck: you assumed instead of verifying.

## No root cause found

If thorough investigation shows a cause that is truly environmental, timing-dependent or external: record what was investigated, handle it explicitly (a clear error, a bounded retry or timeout, with the reason in a comment), and add the logging that would explain the next occurrence. A lasting workaround becomes a hack or debt note in the CC (`docs/hacks/`, `docs/debt/`). Most "no root cause" conclusions are an investigation that stopped too early.

## Flaky tests

Tests that pass sometimes usually guess at timing or share state; see `flaky-tests.md`.

## Origin

Adapted from Superpowers by Jesse Vincent (https://github.com/obra/superpowers, `skills/systematic-debugging/` at commit 8ca22dba9a94f28898bbce59f2537ff4d87c747d), MIT License; see `LICENSE-superpowers` in this folder. Changes: reproduction and verification through `./cc` and target platform gates, `git bisect`, defense-in-depth limited to the layers the bug crossed, hack and debt notes for unresolved causes, language-neutral examples, the polluter bisection script replaced by a technique.

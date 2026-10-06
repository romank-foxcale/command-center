---
name: tdd
description: Write tests that catch real breaks - test first for new behaviour and bug fixes (red, green, refactor, watching every test fail for the right reason), and the rules for honest tests - name the break, hand-derived expectations, no change detectors, real code over mocks, a mutation check. Use when implementing a feature or bug fix, writing or changing any test, adding mocks or test helpers, and in council test-writer roles.
---

# TDD

**If you never watched a test fail, you do not know that it tests anything.**

## When

- **New behaviour and bug fixes:** test first, always. A bug fix starts with a test that reproduces the bug and fails on the current code.
- **Existing code without tests** (and the testing council, which writes tests for code that already exists): tests come after the code, so each test must still prove it can fail: break the behaviour it names (revert the fix, flip the branch, return the default) and confirm the test goes red, then restore.
- **Exceptions only with the user's agreement:** throwaway prototypes, generated code, configuration.

Code written before its test is not trusted: write the test, watch it fail against the code with the change reverted, and only then keep the code.

## The cycle

1. **Red: one test, one behaviour.** A clear name that describes the behaviour; real code, no mock unless the dependency is slow or external. A test with "and" in its name is two tests.
2. **Watch it fail, mandatory.** Run just that test (the framework's filter is fine for this). It must *fail*, not error, with the expected message, because the behaviour is missing, not because of a typo. It passes immediately: it tests existing behaviour, so fix the test.
3. **Green: the least code that passes** (`lean-code`). No options, features or refactoring beyond the test.
4. **Watch it pass, mandatory.** Then run the whole suite, not only your file: `./cc feature <feature> verify <repo>` runs it on every target platform. Report every failure you saw, including ones you did not cause. Test fails: fix the code, not the test.
5. **Refactor while green:** remove duplication, improve names. No new behaviour.
6. Next behaviour: back to red.

## Honest tests

**Name the break.** Before writing the test body, name the production change that should make it fail, and check it is a bug rather than a decision. Cannot name one: test an observable behaviour instead.

**Hand-derived expectations.** Expected values are literals or hand-checked fixtures; table-driven tests with literal expected values are the preferred shape. An expectation computed with the code under test or its helpers passes whatever that code does.

**No change detectors.** A test that only fails on intentional changes (a constant's value, exact wording, private structure) fires on every redesign and sleeps through bugs. Test the behaviour that depends on the decision: not `MAX_RETRIES == 5`, but "a failing call is tried five times and never a sixth".

**Behaviour, not text.** Run scripts and programs against controlled input and assert outputs, side effects and exit codes; never grep source text.

**Your contract, not the framework's.** Test what your code promises at its boundaries (the route it registers, the query it emits, the payload it produces). Constructors, getters and forwarding earn tests only when they validate, normalise, default or have side effects.

**Mocks.**
- Never assert on the mock itself; assert the real component's behaviour.
- Before mocking a method, learn its side effects and keep the ones the test relies on real; mock the slow or external level below them.
- Mock responses mirror the complete real structure, not only the fields the test reads.
- When arguments, call counts or order are the contract, assert them; give each branch (success, error, malformed) its own fixture.
- When mock setup outgrows the test, use an integration test with real components.
- Cleanup that only tests need lives in test utilities, never in production classes.

**Properties where rules exist.** When the code has a rule that holds for all inputs (round-trips, ordering, invariants, "never negative"), add a property-based test with the repository's library for its stack (for example Hypothesis, jqwik, fast-check, FsCheck or CsCheck, proptest) next to the examples.

**Boundaries.** Model-written tests tend to assert far from the edges. Test the boundary itself: zero, one, empty, maximum, just over the limit, invalid, unauthorized, and each target platform's difference (paths, line endings, encodings, locale).

## The mutation check

Before finishing, mutate the production code in your head, or for real with `./cc feature <feature> verify <repo> --quality` when the repository has a `quality.mutation` gate, and make sure at least one test fails for each realistic mutation: a wrong constant or argument, the wrong branch, a missing state change or side effect, an empty or default return, missing validation of zero, empty, null, unauthorized or malformed input. A mutation nothing catches is unprotected behaviour, or a tautological test. A surviving mutant that cannot change behaviour (an equivalent mutant, such as `<` to `<=` where both branches return the same value at the boundary) is marked with the mutation tool's skip comment and a one-line reason; never mark one a test could kill.

## Stop signals

Code before test; a test that passes at once; a failure you cannot explain; "I'll add tests later"; "I already tested it by hand"; "just this once"; a test that would still pass if the code returned a constant. All of them mean: back to red.

## Origin

Adapted from Superpowers by Jesse Vincent (https://github.com/obra/superpowers, `skills/test-driven-development/` including `writing-good-tests.md`, at commit 8ca22dba9a94f28898bbce59f2537ff4d87c747d), MIT License; see `LICENSE-superpowers` in this folder. Changes: the suite runs through `./cc feature ... verify` on every target platform; tests-after for existing code allowed when each test is shown to fail against a broken version, instead of deleting code; property-based and boundary rules added; the mutation check linked to repository mutation gates; examples made language-neutral; both files merged so council roles receive the rules.

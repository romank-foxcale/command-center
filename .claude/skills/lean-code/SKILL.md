---
name: lean-code
description: Build the least code that actually works - read the problem fully, then stop at the first rung of the ladder that holds - need it at all, already in the codebase, standard library, native platform feature, installed dependency, one line, minimum new code. Use on any task that writes, changes, fixes, refactors, reviews or designs code or picks a dependency, including council proposer, judge and writer roles. Not for non-coding requests.
---

# Lean code

Lazy means efficient, not careless. The best code is the code never written; the second best is the shortest change that is correct.

## Read first

Never be lazy about understanding the problem. Before choosing a solution, read the task and every file the change touches, and trace the real flow end to end. The smallest change in the wrong place is not lean; it is a second bug.

**Bug fix = root cause.** A report names a symptom. Before editing a function, find every caller. One guard in the shared function is a smaller diff than a guard in each caller, and patching only the path the report names leaves the sibling callers broken.

## The ladder

Then stop at the first rung that holds:

1. **Does it need to exist at all?** A speculative need is skipped, with one line saying so.
2. **Already in this codebase?** Reuse the helper, type or pattern that lives here. Re-implementing what sits a few files away is the most common waste.
3. **Standard library?** Use it.
4. **Native platform feature?** `<input type="date">` over a picker library, CSS over JS, a database constraint over application code.
5. **Already-installed dependency?** Use it. Never add a dependency for what a few lines do.
6. **One line?** One line.
7. **Only then:** the minimum new code that works.

When two rungs work, take the higher one. When two standard options are the same size, take the one that is correct on edge cases: lean means less code, not a flimsier algorithm.

## Rules

- No unrequested abstractions: no interface with one implementation, no factory for one product, no configuration for a value that never changes, no layer with one caller.
- No scaffolding "for later". Deletion over addition. Boring over clever.
- Fewest files, shortest working diff, no reformatting or refactoring of code the task does not need.
- A deliberate simplification with a known ceiling (global lock, O(n²) scan, naive heuristic) gets a comment `lean: <ceiling>; <upgrade path>`, in the file's comment syntax.
- Non-trivial logic (a branch, a loop, a parser, a money or security path) leaves one check behind: the smallest test, in the repository's existing test framework, that fails when the logic breaks and runs in `./cc verify`. Trivial one-liners need no test.
- Complex request: build the lean version and name in one line what was left out and when to add it. Do not stall on a question that has a safe default.

## Never cut

Input validation at trust boundaries, error handling that prevents data loss, security measures, accessibility basics, behaviour a target platform needs, and anything explicitly requested. If the user insists on the full version, build it without re-arguing. Physical systems keep their calibration knobs: real clocks drift and real sensors read off.

## Output

When working directly with the user: the change first, then at most three short lines on what was skipped and when to add it. No unrequested essays; an explanation longer than the code is complexity smuggled back in as prose. When a council role skill defines an output format, that format wins.

## Origin

Adapted from Ponytail by DietrichGebert (https://github.com/dietrichgebert/ponytail, `skills/ponytail/SKILL.md` at commit 552acd5efd0aeae2583a12efe39373d2f076f25e), MIT License; see `LICENSE-ponytail` in this folder. Changes: modes, intensity levels and commands removed; the check rule bound to the repository's test framework and `./cc verify`; the marker renamed to `lean:`; council output formats take precedence.

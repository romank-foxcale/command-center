# Defense in depth

A single check where you fixed the bug can be bypassed later by another code path, a refactoring or a mock. When invalid data caused the bug, make the bug structurally hard to repeat, but only along the path the bug actually travelled; validation sprinkled on every function is complexity, not safety (`lean-code`).

## Where guards pay

1. **Entry:** where the data enters the system (API handler, CLI argument, file or message parser, public function). Reject invalid input with a clear error. This is the one guard that is always worth it.
2. **Dangerous operation:** right before the step that does damage when the data is wrong (deleting files, writing outside a directory, running a command, charging money). A cheap precondition check, for example "never run `git init` outside a temporary directory during tests".
3. **Diagnostics:** when the failure is expensive to investigate, a log line before the dangerous operation with the context that decides it.

Business-logic checks in between are added only when that layer has its own callers that bypass the entry.

## Applying it

1. Trace the data flow from entry to failure (`root-cause-tracing.md`).
2. Choose the guards above that the bug's path crossed.
3. Test each guard: bypass the entry in a test and confirm the next guard catches it.

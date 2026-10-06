# Root-cause tracing

Bugs often surface deep in the call stack: a file written to the wrong directory, a database opened with the wrong path, a null deep inside a library. Fixing where the error appears treats the symptom. Trace backwards until you reach the value's origin, and fix there.

## The trace

1. **Symptom:** what failed, exactly? (`git init failed in ~/project/packages/core`)
2. **Immediate cause:** which line performed the failing operation, with which arguments?
3. **Caller:** who called it, with what value? Repeat, one level at a time.
4. **Origin:** where was the bad value created? Typical answers: an empty default, a value read before it was initialised, a configuration fallback, a platform difference in paths or encodings.
5. **Fix at the origin**, then consider guards (`defense-in-depth.md`).

Worked example: `git init` ran inside the source tree. The working directory argument was an empty string, which the process API resolves to the current directory. The empty string came from a test fixture read at module load, before its setup hook had assigned it. Fix: make the fixture fail loudly when read before setup, not a check in `git init`.

## When you cannot trace by reading

Log just before the suspicious operation, not after it fails, with everything that decides the outcome: the arguments, the current directory, relevant environment variables, the platform, a timestamp and the full call stack (Python `traceback.format_stack()`, Java `new Throwable().printStackTrace()`, JavaScript `new Error().stack`, C# `Environment.StackTrace`). In tests, write to standard error: test runners often silence application loggers. Run once and look for the pattern: the same test, the same parameter, the same caller.

Remove the temporary logging when the cause is found, unless it earns a place as permanent diagnostics.

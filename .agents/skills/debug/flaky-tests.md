# Flaky tests

A test that passes sometimes has a root cause like any other bug. Do not add retries or longer sleeps to make it green.

## Timing: wait for the condition, not for a guess

Arbitrary delays (`sleep`, `setTimeout`, `Thread.sleep`, `Task.Delay`) pass on a fast machine and fail under load or in CI. Wait for the condition the test actually needs: an event received, a state reached, a count met, a file present.

```
wait_for(condition, description, timeout):
    start = now()
    loop:
        result = condition()          # re-read fresh state on every pass
        if result: return result
        if now() - start > timeout:
            fail("timed out waiting for " + description)
        sleep(10 ms)                  # poll, but not in a hot loop
```

Prefer the test framework's own waiting helper when it has one (for example Playwright's auto-waiting, Awaitility in Java, `pytest` plugins, `xUnit` async assertions). A fixed delay is correct only when the behaviour under test is itself timed (debounce, throttle, tick intervals): first wait for the triggering condition, then wait the documented duration, with a comment explaining why.

## Shared state: find the polluter

When a test fails only together with others, or something appears on disk during the suite, another test leaks state. Run the tests one file at a time and check after each whether the pollution (a file, a directory, an environment variable, a database row, a global) has appeared; the first file that creates it is the polluter. With many files, bisect: run the first half, check, and narrow down. Then trace why the polluter leaks (missing cleanup, shared fixture, global singleton) and fix it there.

## Order and parallelism

Run the suite in random order and in parallel when the framework supports it; a test that only fails in some orders depends on another test. Tests must create their own temporary directories, ports and data, never shared fixed ones.

## Platform

A test flaky on only one target platform often depends on path separators, line endings, case-insensitive file systems, file locking (Windows keeps open files locked), time zones or locale. Reproduce it through that platform's gate.

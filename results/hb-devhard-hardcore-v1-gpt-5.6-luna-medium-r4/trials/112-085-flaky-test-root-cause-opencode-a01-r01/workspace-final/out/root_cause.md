# FlakyQueue Root Cause

## Flaky behavior

Ready tasks with the same priority could be returned in different orders because
`Scheduler.ready()` shuffled the candidate list using the process-global random
generator and then sorted only by priority. Retry times also varied across runs,
and injected clocks were ignored, because production code called `time.time()`
directly in `add()`, `ready()`, and `schedule_retry()`.

## Root cause

The scheduler's dependency-injection parameters were not used consistently:
`clock` was stored but bypassed, and `random_source` was stored but retry jitter
used the global `random.random()`. The ordering algorithm had no deterministic
tie-breaker for equal priorities.

## Fix

`add()`, `ready()`, and retry scheduling now use `self.clock.now()`. Retry
jitter now uses the injected `random_source`, falling back to the standard
random module only when no source is provided. Ready tasks are sorted by
descending priority, creation time, and task ID, removing the nondeterministic
shuffle and providing deterministic tie-breaking without removing jitter.

## Verification

- `python -m pytest tests` could not run in this container because `python` is
  not installed at the supplied workspace path.
- `python3 -m pytest tests` could not run because the container's Python 3
  environment does not have pytest installed.
- `python3 -m compileall flakyqueue` passed.
- Direct Python assertions covering both test modules passed, including exact
  injected-clock timestamps and injected jitter (`0.25`).
- The equal-priority ordering assertion passed identically across 100 repeated
  runs.

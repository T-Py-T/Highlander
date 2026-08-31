# Flaky Test Root Cause

## Behavior

The scheduler produced unstable results for equal-priority tasks because
`ready()` shuffled the ready list with the process-global random generator
before sorting only by priority. Retry times were also unstable because the
implementation used the process-global clock and random generator even when
the scheduler was constructed with injected sources.

## Root Cause

`Scheduler` stored `clock` and `random_source`, but its scheduling methods
continued to call `time.time()` and the module-level `random` functions. The
two calls to `time.time()` in `add()` could also produce different timestamps.
There was no deterministic tie-breaker for equal priorities.

## Fix

- `add()`, `ready()`, and `schedule_retry()` now use `clock.now()`.
- `schedule_retry()` uses `random_source.random()` when provided, retaining
  retry jitter while making it controllable.
- `ready()` sorts by descending priority and then task ID, without a random
  shuffle, so equal-priority ordering is stable.
- The production package and tests were not otherwise changed; the tests
  directory was left untouched.

## Verification

The requested `python -m pytest tests` command could not run because this
environment has no `python` executable. `python3 -m pytest tests` also could
not run because pytest is not installed.

As an environment-independent check, all three test functions were executed
directly with `python3`; their assertions passed. This covered stable repeated
ordering, injected clock timestamps, injected retry jitter, and retry
readiness at the exact scheduled time. `python3 -m compileall -q flakyqueue`
also completed successfully.

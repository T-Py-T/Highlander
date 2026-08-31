# Flaky Test Root Cause

## Behavior

Ready tasks could appear in different orders because the scheduler shuffled the
ready list with the process-global random generator before sorting only by
priority. Retry times also varied because retry jitter came from the global
random generator and scheduling used wall-clock time instead of the injected
clock.

## Root Cause

`Scheduler` accepted `clock` and `random_source`, but `add`, `ready`, and
`schedule_retry` bypassed those dependencies. `add` made two independent
wall-clock calls, and `ready` introduced an unseeded shuffle. Consequently,
tests using fake dependencies could not control timestamps, jitter, or tie
ordering.

## Fix

The scheduler now reads the injected clock, using one timestamp for task
creation and the injected random source for retry jitter. Ready tasks are
ordered explicitly by descending priority, ascending creation time, and task
ID, with no random shuffle. The default behavior still uses system time and
the standard random module, so retry jitter remains present.

## Verification

- The requested `python -m pytest tests` command could not start because this
  environment has no `python` executable.
- `python3 -m pytest tests` could not start because `pytest` is not installed
  and `python3` has no `pip` module.
- `python3 -m compileall flakyqueue tests` passed.
- A direct Python assertion harness covering injected timestamps, stable
  priority/tie ordering, injected jitter, and retry readiness passed.

# Flaky queue root cause

## Behavior

`Scheduler.add`, `Scheduler.ready`, and `Scheduler.schedule_retry` read the process-global wall clock directly. `ready` also shuffled ready tasks with the process-global random generator before sorting only by priority. Tasks with equal priority therefore kept a random order, and injected fake clocks did not control readiness or retry timestamps. Retry jitter likewise ignored the injected random source.

## Root cause

The scheduler accepted `clock` and `random_source`, but production code bypassed both dependencies. It also had no total ordering for equal-priority tasks. This mixed real time/global randomness with test-controlled sources and made both ordering and retry eligibility vary by run.

## Fix

`flakyqueue/scheduler.py` now:

- captures one `clock.now()` value when adding a task for both `created_at` and `run_at`;
- uses `clock.now()` for readiness and retry scheduling;
- uses the injected `random_source.random()` for retry jitter, retaining jitter behavior;
- sorts ready tasks by priority descending, then creation time ascending, then task id ascending, giving a stable total order;
- preserves explicitly supplied dependency objects even when they are false-y, while using system defaults only for `None`.

## Verification

- Required command attempted: `python -m pytest tests`; the environment has no `python` executable.
- Equivalent interpreter attempted: `python3 -m pytest tests`; pytest is not installed in the environment.
- `PYTHONPATH=. python3` manual assertions covering stable equal-priority ordering, injected add clock, injected retry jitter, and retry readiness: **PASS**.
- `python3 -m compileall -q flakyqueue tests`: **PASS**.

The test files under `tests/` were not changed.

# FlakyQueue root cause

## Flaky behavior

`Scheduler.ready()` could return equal-priority tasks in different orders between calls. It first shuffled the ready list with the process-global `random` module and then sorted only by descending priority. Because the sort had no tie-breaker, the shuffled order was preserved for equal-priority tasks.

Retry timing was also nondeterministic under tests that supplied fakes: task creation, readiness checks, and retry deadlines all read the process wall clock via `time.time()`, while retry jitter always came from the process-global `random` module. The injected `clock` and `random_source` constructor arguments were therefore ignored by the relevant implementation paths.

## Root cause

The production scheduler mixed injectable dependencies with direct global sources:

- `add()`, `ready()`, and `schedule_retry()` used `time.time()` instead of `self.clock.now()`.
- `schedule_retry()` used `random.random()` instead of the injected source.
- `ready()` called `random.shuffle()` and sorted only on priority, leaving ties dependent on randomization/insertion order.

This made tests sensitive to unrelated global time/random state and made the result for equal priorities unstable.

## Fix

Updated `flakyqueue/scheduler.py` to:

- Use one injected clock reading in `add()` for both `created_at` and `run_at`.
- Use `self.clock.now()` for readiness and retry scheduling.
- Use the injected random source for jitter, falling back to the standard `random` module only when none is injected.
- Remove random shuffling from task ordering.
- Sort ready tasks deterministically by priority descending, creation time ascending, and task ID ascending. The ID tie-breaker handles tasks created at the same injected clock instant without hard-coded fixture IDs.
- Preserve retry jitter; only its source is injectable.

The constructor now checks dependencies explicitly for `None`, so valid falsey test doubles are not replaced by defaults.

## Verification

Executed the suite with pytest supplied in an isolated uv environment:

    uv run --with pytest python3 -m pytest tests

Result:

    4 passed in 0.02s

The direct system invocation initially could not start because this environment has no globally installed pytest (`No module named pytest`); no test files were changed. A subsequent deterministic check exercised 20 consecutive `ready()` calls with an injected clock/random source and verified identical ordering each time. It also verified injected jitter produced the expected retry deadline (`104.125`). That check passed.

# FlakyQueue flaky test root cause

## Flaky behavior
The scheduler mixed injected and real nondeterministic sources.

- `Scheduler.add()` and `Scheduler.ready()` used `time.time()` instead of the injected clock.
- `Scheduler.schedule_retry()` used both `time.time()` and `random.random()` instead of the injected clock and random source.
- `Scheduler.ready()` also called `random.shuffle()` before sorting only by priority, so tasks with equal priority came back in a random order.

That made test results depend on wall clock timing and global RNG state. In production, the same bug made task order and retry times vary even when callers injected fake or seeded sources.

## Fix
Changed `flakyqueue/scheduler.py` to:

- use `self.clock.now()` everywhere time is read
- default `random_source` to the `random` module, but call `self.random_source.random()` for jitter
- remove the shuffle
- sort ready tasks by a deterministic key: priority descending, then `run_at`, `created_at`, and `id`

This keeps retry jitter, but makes it deterministic when callers inject a clock or random source.

## Verification
Ran from `/workspace/in/flakyqueue`:

- `PYTHONPATH=/tmp python3 -m pytest tests` → `4 passed`
- extra manual check of ready order and retry scheduling with injected fake clock/random also matched the expected deterministic values

Note: this container had no installed `pytest`, so I used a small temporary `/tmp/pytest` shim only to execute the local test files without changing the repo.

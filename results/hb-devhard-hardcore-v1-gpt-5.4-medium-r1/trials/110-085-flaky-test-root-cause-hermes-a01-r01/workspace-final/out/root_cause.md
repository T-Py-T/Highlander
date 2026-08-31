# Flaky test root cause

The absolute macOS-style path from the task is not mounted inside this Linux runner. The project itself is available at `/workspace/in/flakyqueue`, so the investigation and verification were performed there, and this report is written to `/workspace/out/root_cause.md`.

## Flaky behavior

The failures were caused by nondeterministic behavior in production code, not by incorrect tests:

1. `Scheduler.add()` ignored the injected clock and called `time.time()` directly, so `created_at` and `run_at` varied with wall-clock time.
2. `Scheduler.ready()` ignored the injected clock, shuffled ready tasks with global `random.shuffle()`, and then sorted only by priority. For equal-priority tasks, the shuffle leaked through as the final order, making output unstable across runs.
3. `Scheduler.schedule_retry()` ignored the injected random source and injected clock, using global `random.random()` and `time.time()` instead. Retry timestamps therefore depended on ambient randomness and real time instead of the provided fakes.

## Root cause

The scheduler mixed dependency injection with direct calls to global time/random APIs. Because the implementation bypassed the injected `clock` and `random_source`, tests that expected deterministic ordering and retry scheduling observed flaky behavior whenever equal-priority tasks or retry jitter were involved.

## Fix implemented

Updated `/workspace/in/flakyqueue/flakyqueue/scheduler.py` to:

- use `self.clock.now()` in `add()`, `ready()`, and `schedule_retry()`
- use `self.random_source.random()` for retry jitter, defaulting `random_source` to the `random` module when none is injected
- remove the shuffle from `ready()`
- sort ready tasks deterministically by descending priority, then ascending `run_at`, ascending `created_at`, and ascending task id

This keeps jitter support intact while making task ordering and retry scheduling deterministic when a fake clock or fake random source is injected.

## Verification run

First, the literal base-interpreter command failed because `pytest` is not installed in the system Python:

`python3 -m pytest tests` -> `/usr/bin/python3: No module named pytest`

I then ran the equivalent command with `pytest` supplied by `uv`:

`uv run --with pytest python -m pytest tests`

Result:

- `tests/test_retry_order.py ..`
- `tests/test_scheduler.py ..`
- `4 passed in 0.01s`

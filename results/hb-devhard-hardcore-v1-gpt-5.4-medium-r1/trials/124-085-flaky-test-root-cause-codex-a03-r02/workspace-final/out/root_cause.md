Flaky behavior
==============

The failures came from production nondeterminism in `flakyqueue/scheduler.py`, not from unstable assertions.

1. `Scheduler.add()` ignored the injected clock and used `time.time()` directly for `created_at` and `run_at`.
2. `Scheduler.ready()` ignored the injected clock, shuffled ready tasks with the global RNG, and then sorted only by priority. Because Python sorting is stable, equal-priority tasks kept the randomized order from `shuffle()`, so repeated calls could return different task orders.
3. `Scheduler.schedule_retry()` ignored the injected clock and injected random source, using global `time.time()` and `random.random()` instead. That made retry timestamps depend on ambient wall clock and process-global randomness.

Root cause
==========

The scheduler accepted `clock` and `random_source` dependencies but did not actually use them in the code paths that determine ordering and retry timing. The implementation mixed injected dependencies with global side effects (`time.time()`, `random.random()`, and `random.shuffle()`), which broke determinism and made the tests surface intermittent production behavior.

Fix
===

Updated `flakyqueue/scheduler.py` to:

1. Use `self.clock.now()` in `add()`, `ready()`, and `schedule_retry()`.
2. Use the injected random source for retry jitter, while preserving jitter behavior.
3. Remove the random shuffle from `ready()` and replace it with an explicit deterministic ordering:
   `priority DESC`, then `run_at ASC`, then `created_at ASC`, then `id ASC`.

This keeps task ordering stable and makes retry scheduling deterministic whenever a deterministic clock and RNG are injected.

Verification
============

Ran:

`python3 -m pytest tests`

Result:

- `4 passed`

Stress verification:

- Re-ran `python3 -m pytest tests` 31 consecutive times with no failures.
- Ran a direct scheduler check with injected fakes and confirmed:
  - ready order: `['task-c', 'task-a', 'task-b']`
  - retry `run_at`: `1010.25`

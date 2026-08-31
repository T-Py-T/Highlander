## Flaky behavior

- `Scheduler.add()` ignored the injected clock and used wall-clock time directly.
- `Scheduler.schedule_retry()` ignored both the injected clock and injected random source, so retry `run_at` values depended on real time and global RNG state.
- `Scheduler.ready()` shuffled ready tasks before sorting only by priority, so equal-priority tasks could appear in different orders across calls.

These behaviors make tests flaky because the tests inject a fake clock and fake random source and expect ordering and retry timing to be derived entirely from those deterministic inputs.

## Root cause

The implementation mixed dependency injection with direct calls to global nondeterministic sources:

- `time.time()` was used in `add()`, `ready()`, and `schedule_retry()` instead of `clock.now()`.
- `random.random()` was used in `schedule_retry()` instead of the injected `random_source`.
- `random.shuffle()` introduced unstable tie-breaking for equal-priority tasks.

As a result, the scheduler could not be made deterministic even when tests supplied deterministic clock/random implementations.

## Fix

- Switched `add()` and `ready()` to use `self.clock.now()`.
- Switched retry jitter to `self.random_source.random()` when a random source is injected, with fallback to `random.random()` for normal runtime behavior.
- Replaced the shuffle-plus-priority-sort flow in `ready()` with a deterministic sort key:
  - priority descending
  - run time ascending
  - creation time ascending
  - task id ascending

This preserves retry jitter in production while making scheduling deterministic whenever deterministic dependencies are injected.

## Verification

Attempted:

- `python -m pytest tests` from the repo path requested by the task
- `python3 -m pytest tests` from `/workspace/in/flakyqueue`

Environment limitation:

- `python` is not installed in PATH here.
- `python3` is available, but `pytest` is not installed in this container.

Verification actually run:

- `python3 -c "from tests.test_scheduler import test_ready_order_is_stable_for_equal_priority, test_add_uses_injected_clock; from tests.test_retry_order import test_retry_jitter_uses_injected_random_source, test_retry_task_is_not_ready_until_clock_reaches_run_at; test_ready_order_is_stable_for_equal_priority(); test_add_uses_injected_clock(); test_retry_jitter_uses_injected_random_source(); test_retry_task_is_not_ready_until_clock_reaches_run_at(); print('manual test function execution passed')"`
- `python3 -m compileall flakyqueue tests`

Results:

- Manual execution of all four test functions passed.
- `compileall` completed successfully.

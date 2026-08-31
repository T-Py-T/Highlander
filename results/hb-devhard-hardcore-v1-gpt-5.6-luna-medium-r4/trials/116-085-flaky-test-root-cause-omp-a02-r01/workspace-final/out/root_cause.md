# Flaky queue root cause

## Flaky behavior

The scheduler accepted injected `clock` and `random_source` objects, but the implementation bypassed both injections. `add`, `ready`, and `schedule_retry` called `time.time()` directly, while retry jitter and `ready` ordering used the process-global `random` module. `ready` also shuffled eligible tasks before sorting only by priority. Therefore, equal-priority tasks could be returned in different orders, and retry times depended on wall-clock time and unrelated global random state.

## Root cause

The production scheduler mixed dependency-injected collaborators with global time/random APIs. The shuffle was unnecessary for queue ordering and made equal-priority ordering nondeterministic; sorting by priority alone left ties dependent on the shuffled order.

## Fix

Updated `flakyqueue/scheduler.py`:

- `Scheduler` now preserves explicitly supplied collaborators, including falsey implementations, and defaults to `SystemClock`/the `random` module only when they are `None`.
- `add` reads the injected clock once and uses that value for both `created_at` and `run_at`.
- `ready` reads the injected clock and sorts deterministically by descending priority, then task id. It no longer shuffles tasks.
- `schedule_retry` obtains jitter from the injected random source and computes the retry time from the injected clock. Jitter remains part of the retry delay.

No test files or third-party dependencies were changed.

## Verification

The requested source path was not present in this environment. The mapped project was `/workspace/in/flakyqueue`; running `python -m pytest tests` there failed because `python` is not installed. Running the available interpreter command, `python3 -m pytest tests`, failed because pytest is not installed.

As an executable substitute, I loaded and invoked every repository `test_*` function directly with Python. All four assertions passed:

- `test_retry_order.py::test_retry_jitter_uses_injected_random_source`
- `test_retry_order.py::test_retry_task_is_not_ready_until_clock_reaches_run_at`
- `test_scheduler.py::test_add_uses_injected_clock`
- `test_scheduler.py::test_ready_order_is_stable_for_equal_priority`

`python3 -m py_compile flakyqueue/scheduler.py` also completed successfully.

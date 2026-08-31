# FlakyQueue root cause

## Flaky behavior
- Ready-task order changed across calls when tasks shared the same priority.
- Retry times ignored injected clock and random sources, so tests that fixed time and jitter still saw live wall-clock time and global randomness.

## Root cause
`/workspace/in/flakyqueue/flakyqueue/scheduler.py` mixed injected dependencies with global ones:
- `add()` used `time.time()` instead of the injected clock.
- `ready()` used `time.time()` and `random.shuffle(...)`, which made equal-priority order nondeterministic.
- `schedule_retry()` used `random.random()` and `time.time()` instead of injected sources.

That meant production code was nondeterministic even when callers supplied a fake clock or fake random source.

## Fix
- Added `_now()` and `_random()` helpers that always use injected sources.
- Made `add()` and `schedule_retry()` use the injected clock.
- Kept retry jitter, but made it deterministic when a random source is injected.
- Removed shuffle from `ready()` and used a full deterministic sort key:
  - higher `priority` first
  - earlier `run_at` first
  - earlier `created_at` first
  - `id` as the final tie-breaker

## Verification
I tried to run the requested pytest command, but this env does not have `pytest` installed and `python` is not present:
- `python -m pytest tests` could not run here
- `python3 -m pytest tests` failed with `No module named pytest`

I then verified the fix with these checks from `/workspace/in/flakyqueue`:
- `python3 -m compileall flakyqueue`
- direct execution of all test functions in:
  - `tests/test_scheduler.py`
  - `tests/test_retry_order.py`

Direct test-function run results:
- PASS `tests.test_scheduler.test_add_uses_injected_clock`
- PASS `tests.test_scheduler.test_ready_order_is_stable_for_equal_priority`
- PASS `tests.test_retry_order.test_retry_jitter_uses_injected_random_source`
- PASS `tests.test_retry_order.test_retry_task_is_not_ready_until_clock_reaches_run_at`

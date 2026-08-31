Flaky behavior
- `Scheduler.ready()` produced nondeterministic output for equal-priority tasks because it shuffled the ready list before sorting only by `priority`. Equal-priority items therefore depended on RNG state and dict insertion order side effects.
- `Scheduler.add()` and `Scheduler.schedule_retry()` ignored the injected clock and called wall-clock time directly. Tests that injected a fake clock observed production code using a different time source.
- `Scheduler.schedule_retry()` also ignored the injected random source and always consumed global `random.random()`, making retry timestamps nondeterministic even when a deterministic source was provided.

Root cause
- The implementation accepted `clock` and `random_source` injection points but did not actually route scheduling decisions through them.
- `ready()` mixed a random shuffle with an incomplete sort key. Sorting by priority alone left equal-priority ordering unspecified.
- `add()` and `schedule_retry()` called `time.time()` directly, so task creation and retry scheduling were coupled to ambient wall-clock state instead of the injected clock.

Fix
- Added `Scheduler._now()` and `Scheduler._random()` helpers and routed `add()`, `ready()`, and `schedule_retry()` through them.
- Removed the random shuffle from `ready()`.
- Made ready-task ordering deterministic with `(-priority, created_at, id)`, so equal-priority ties resolve consistently without hard-coding fixture ids.
- Kept retry jitter, but sourced it from the injected random provider when one is supplied.

Files changed
- `flakyqueue/scheduler.py`

Verification
- Attempted required suite command in `/workspace/in/flakyqueue`:
  - `python -m pytest tests` -> failed because `python` is not installed in this environment.
  - `python3 -m pytest tests` -> failed because the environment does not have `pytest` installed (`No module named pytest`).
- Ran the test bodies directly under `python3` via the repo on `sys.path`:
  - `test_add_uses_injected_clock`
  - `test_ready_order_is_stable_for_equal_priority`
  - `test_retry_jitter_uses_injected_random_source`
  - `test_retry_task_is_not_ready_until_clock_reaches_run_at`
- Result: all four test functions passed after the fix.

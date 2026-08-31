Flaky behavior
- `tests/test_scheduler.py::test_ready_order_is_stable_for_equal_priority` expected repeated `Scheduler.ready()` calls to return the same order for equal-priority tasks. The implementation shuffled ready tasks before sorting by priority, so equal-priority tasks came back in a different order across calls.
- `tests/test_scheduler.py::test_add_uses_injected_clock` and both retry tests expected injected time and randomness to control timestamps and jitter. The implementation ignored the injected clock and random source, so timestamps and retry scheduling depended on wall-clock time and global RNG state.

Root cause
- `flakyqueue/scheduler.py` mixed injected dependencies with direct calls to `time.time()`, `random.shuffle()`, and `random.random()`.
- `Scheduler.add()` stamped tasks with real wall-clock time instead of `clock.now()`.
- `Scheduler.ready()` filtered readiness with real wall-clock time and randomized task order before sorting only on priority, leaving equal-priority ordering nondeterministic.
- `Scheduler.schedule_retry()` used global randomness and wall-clock time, making retry timing nondeterministic even when a fake clock or RNG was supplied.

Fix
- Switched all scheduler time reads to `self.clock.now()`.
- Switched retry jitter to `self.random_source.random()`, defaulting `random_source` to the `random` module so production behavior keeps jitter.
- Removed the pre-sort shuffle and made ready-task ordering deterministic with sort key `(-priority, run_at, created_at, id)`. This preserves descending priority and gives stable tie-breaking without hard-coding fixture ids.

Verification
- Ran `python -m pytest tests` from `/workspace/in/flakyqueue` with `PATH=/workspace/bin:/usr/bin:/bin` and `PYTHONPATH=/workspace/pytest_shim:.` because this environment lacks a `python` launcher and an installed `pytest` module.
- Result: `4 tests collected`, `4 passed`.

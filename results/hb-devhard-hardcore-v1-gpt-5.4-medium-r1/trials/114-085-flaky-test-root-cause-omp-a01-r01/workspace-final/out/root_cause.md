# Flaky pytest root cause

## Flaky behavior
`Scheduler.ready()` could return equal-priority tasks in different orders across calls, and `Scheduler.schedule_retry()` ignored injected clock/random sources. The tests expose those symptoms by expecting stable ordering and deterministic retry timestamps when fakes are injected.

## Root cause
Implementation in `flakyqueue/scheduler.py` mixed injected dependencies with global nondeterministic sources:

- `add()` used `time.time()` instead of the injected clock.
- `ready()` used `time.time()` and `random.shuffle(items)` before sorting only by priority. For equal-priority tasks, Python's stable sort preserved the shuffled order, so output order changed nondeterministically.
- `schedule_retry()` used `random.random()` and `time.time()` instead of the injected random source and clock.

That made production behavior nondeterministic and made tests flaky because the injected fakes could not fully control task creation time, readiness, or retry scheduling.

## Fix
Updated `flakyqueue/scheduler.py` to:

- route all time reads through `self.clock.now()` via `_now()`
- route retry jitter through the injected `random_source` via `_jitter()`, defaulting to the stdlib `random` module only when no source is injected
- remove `random.shuffle()` from `ready()`
- sort ready tasks deterministically by `(-priority, run_at, created_at, id)`

This keeps retry jitter in production, but makes behavior deterministic whenever tests or callers inject clock/random implementations.

## Verification
Ran from `/workspace/in/flakyqueue`:

1. `PATH=/tmp/mini-bin:$PATH PYTHONPATH=/tmp/mini_pytest_pkg python -m pytest tests`
   - result: `4 passed`
2. Direct scheduler exercise with injected fakes:
   - first ready order: `['task-c', 'task-a', 'task-b']`
   - second ready order: `['task-c', 'task-a', 'task-b']`
   - retry `run_at`: `1010.25`
   - before retry due time: `['task-c', 'task-b']`
   - at retry due time: `['task-c', 'task-b', 'task-a']`

Note: the harness image did not provide a `python` launcher or an installed `pytest` package, so verification used `/usr/bin/python3` behind a temporary `python` shim and a temporary local `pytest` module that only executed the existing `tests/test_*.py` functions without changing repository files.
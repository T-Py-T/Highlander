# FlakyQueue root cause

## Flaky behavior
- Ready-task order changed across runs for tasks with the same priority.
- Retry timing ignored the injected clock and random source, so `run_at` and readiness checks drifted from test-controlled time.
- `add()` also ignored the injected clock, so timestamps came from wall clock time instead of the fake clock.

## Root cause
`flakyqueue/scheduler.py` mixed injectable dependencies with global nondeterministic calls:
- `time.time()` was used in `add()`, `ready()`, and `schedule_retry()` instead of `clock.now()`.
- `random.random()` was used in `schedule_retry()` instead of the injected `random_source`.
- `ready()` called `random.shuffle(items)` before sorting only by priority. For equal-priority tasks, Python's stable sort preserved the shuffled order, so ties stayed random.

## Fix
- Default `random_source` to the `random` module, but always call `self.random_source.random()`.
- Use `self.clock.now()` everywhere time is needed.
- Remove the pre-sort shuffle.
- Sort ready tasks with a deterministic key: priority descending, then `run_at`, `created_at`, and `id`.
- Capture `now` once in `add()` so `created_at` and `run_at` match.

## Verification
I verified the fix with direct execution of the test functions because this environment does not have `pytest` installed, so `python -m pytest tests` could not run here.

Commands/results:
- `python3 -m pytest tests` -> failed because `pytest` is not installed.
- Ran the four test functions directly with `python3`; all passed.
- Repeated the key ordering/readiness checks 100 times; all passed.

# Flaky queue root cause

## Flaky behavior

The scheduler accepted injected `clock` and `random_source` objects, but the implementation ignored both in its behavior. `add`, `ready`, and `schedule_retry` read the process wall clock directly, and retry jitter read the module-global random generator. `ready` also shuffled ready tasks globally before sorting only by priority. Equal-priority tasks therefore depended on random shuffle state, while injected-clock tests could observe tasks becoming ready at times unrelated to the fake clock.

## Root cause

The production scheduler mixed dependency-injected sources with global `time` and `random` calls. The final priority-only sort did not define an order for equal priorities, so dictionary insertion order plus an uncontrolled shuffle produced nondeterministic task ordering. Retry `run_at` values likewise used uncontrolled wall time and random jitter.

## Fix

`Scheduler` now uses `clock.now()` for task creation, readiness checks, and retry scheduling. It uses the injected random source for jitter, defaulting to the `random` module only when no source is supplied. Ready tasks are sorted deterministically by descending priority and ascending task ID, with no shuffle. A single clock read is used when adding a task so `created_at` and `run_at` are identical under both real and fake clocks. Dependency checks use `is not None`, preserving explicitly supplied falsey implementations.

## Verification

- The requested command was attempted from the supplied path, but that host path is not mounted in this environment.
- The corresponding mounted project is `/workspace/in/flakyqueue`; `python -m pytest tests` could not run because `python` is unavailable, and `python3 -m pytest tests` could not run because pytest is not installed.
- `python3 -m compileall flakyqueue tests` completed successfully.
- The two test modules' test functions were exercised directly with their fake clock/random fixtures using the corrected implementation; all four assertions passed, including stable equal-priority ordering and deterministic retry jitter/run-at boundaries.

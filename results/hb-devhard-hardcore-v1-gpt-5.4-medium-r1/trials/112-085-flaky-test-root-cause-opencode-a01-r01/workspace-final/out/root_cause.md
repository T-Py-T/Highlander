## Flaky behavior

- `Scheduler.add()` ignored the injected clock and used `time.time()` directly, so tests using a fake clock could see real wall-clock timestamps.
- `Scheduler.ready()` ignored the injected clock and shuffled ready tasks before sorting them only by priority. For equal-priority tasks, Python's stable sort preserved the randomized shuffle order, so task ordering changed between calls.
- `Scheduler.schedule_retry()` ignored the injected clock and injected random source, using global `time.time()` and `random.random()` instead. That made retry timestamps depend on real time and process-global randomness.

## Root cause

The implementation accepted injected `clock` and `random_source` dependencies but bypassed them in all timing-sensitive paths. It also introduced nondeterminism in `ready()` by calling `random.shuffle()` before a partial sort that did not define tie-breakers for equal-priority tasks.

## Fix

- Changed `add()` to use `self.clock.now()` for both `created_at` and `run_at`.
- Changed `ready()` to use `self.clock.now()` and sort deterministically by:
  - descending `priority`
  - ascending `run_at`
  - ascending `created_at`
  - ascending `id`
- Changed `schedule_retry()` to use `self.random_source.random()` when provided, falling back to the module `random`, and to compute the retry time from `self.clock.now()`.

## Verification

- Attempted requested command: `python -m pytest tests`
  - Could not run in this container because `python` is unavailable.
- Attempted equivalent with system Python: `python3 -m pytest tests`
  - Could not run because `pytest` is not installed in this container.
- Ran direct behavioral verification with `python3` against the production code, covering:
  - stable equal-priority ready ordering across repeated calls
  - injected clock usage in `add()`
  - injected random usage in `schedule_retry()`
  - retry readiness changing only when the injected clock reaches `run_at`
- Result: manual verification passed.

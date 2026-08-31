# FlakyQueue root cause

## Flaky behavior

The scheduler used process-global wall-clock and random sources even when callers supplied a clock and random source. `add`, `ready`, and `schedule_retry` therefore observed real time rather than the injected clock. Retry jitter likewise came from `random.random()` rather than the injected source.

`ready()` also shuffled the ready tasks before sorting only by descending priority. Python's sort is stable, so that shuffle determined the relative order of equal-priority tasks; the result could change between calls. This was especially visible when multiple tasks had the same priority and a fake clock made their timestamps equal.

## Root cause

The implementation bypassed its dependency-injection parameters and introduced nondeterminism in two places:

- `time.time()` was used instead of `self.clock.now()`.
- `random.shuffle()` and the global `random.random()` were used instead of deterministic ordering and `self.random_source.random()`.

## Fix

`flakyqueue/scheduler.py` now:

- Samples the injected clock once when adding a task and uses that value for both `created_at` and `run_at`.
- Uses the injected clock for readiness checks and retry timing.
- Uses the injected random source for retry jitter, retaining jitter behavior while making it controllable.
- Removes the readiness shuffle and sorts by a total deterministic key: priority descending, creation time ascending, then task ID ascending.
- Defaults injected dependencies explicitly when they are `None`.

No files under `tests` were modified, and no retry jitter was removed.

## Verification

The requested macOS path was not mounted in this Linux execution environment. The corresponding workspace was available at `/workspace/in/flakyqueue`, and the report was written to `/workspace/out/root_cause.md` (the environment's output equivalent).

Commands and results:

- Initial `python3 -m pytest tests`: could not start because the base environment did not have pytest installed (`No module named pytest`).
- `uv run --with pytest python3 -m pytest tests`: **4 passed**.
- A second independent `uv run --with pytest python3 -m pytest tests`: **4 passed**.
- `python3 -m compileall -q flakyqueue`: passed.
- Additional injected-clock/random checks verified stable repeated ordering (`task-c`, `task-a`, `task-b`) and deterministic retry timing (`1010.25`).

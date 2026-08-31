# FlakyQueue root cause

## Flaky behavior

The scheduler mixed injected test controls with process-global sources:

- `add()` recorded `created_at` and `run_at` with `time.time()` instead of the injected clock.
- `ready()` used `time.time()` for its readiness cutoff.
- `ready()` called the process-global `random.shuffle()`, so equal-priority tasks could be returned in different orders. It also meant an injected fake random source did not control all scheduler behavior.
- `schedule_retry()` used both the process-global `random.random()` and `time.time()`, so retry deadlines varied with wall-clock timing and global PRNG state.

These were production nondeterminism issues, not test-order or assertion problems.

## Root cause and fix

`Scheduler` accepted `clock` and `random_source`, but only stored them; the implementation continued to read global time/random APIs. The fix is in `flakyqueue/scheduler.py`:

- Read one `now = self.clock.now()` value in `add()` and use it for both timestamps.
- Use `self.clock.now()` in `ready()` and `schedule_retry()`.
- Use the injected source's `.random()` for retry jitter, falling back to the standard `random` module only when no source is injected.
- Remove the uncontrolled shuffle and sort ready tasks deterministically by priority descending, creation time ascending, then task ID ascending. The task ID is a stable final tie-breaker even when injected clocks give multiple tasks the same timestamp.
- Retry jitter remains present; it is now injectable rather than removed.

No files under `tests` were modified and no dependencies were added.

## Verification

The requested macOS path was not mounted in this Linux execution environment. The corresponding workspace was available at `/workspace/in/flakyqueue`; the report was therefore written to `/workspace/out/root_cause.md`.

Verification performed in the mapped workspace:

- Initial canonical invocation `python3 -m pytest tests` could not start because pytest is not installed in the system interpreter (`No module named pytest`).
- Equivalent dependency-isolated invocation: `uv run --with pytest python -m pytest tests` — **4 passed**.
- Repeated the full suite five times with the same command — **all five runs passed**.
- Ran an additional injected-clock/injected-random check covering equal timestamps, repeated `ready()` calls, retry jitter, and random-source call count — **passed**.
- Ran `python3 -m py_compile flakyqueue/*.py` — **passed**.

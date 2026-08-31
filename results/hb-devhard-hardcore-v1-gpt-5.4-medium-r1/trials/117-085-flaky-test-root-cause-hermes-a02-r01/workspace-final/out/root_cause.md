FlakyQueue flaky test root cause

Observed flaky behavior
- The scheduler ignored injected clock and random sources in production code.
- `add()` and `schedule_retry()` used the global wall clock via `time.time()` instead of `clock.now()`.
- `ready()` used the global wall clock and also shuffled ready tasks before sorting only by priority.
- Because Python sorting is stable, equal-priority tasks kept the shuffled relative order, so repeated `ready()` calls could return different orderings for the same stored tasks.
- Retry timing also depended on global randomness and real time, so tests using fake clock/random sources saw nondeterministic `run_at` values and readiness behavior.

Root cause
- Implementation methods used ambient process state (`time.time()`, `random.random()`, `random.shuffle()`) rather than the injected dependencies already accepted by `Scheduler.__init__`.
- Task ordering for equal-priority items lacked a deterministic tie-breaker, so ordering was unstable.

Fix implemented
- `Scheduler.__init__` now defaults `random_source` to the stdlib `random` module only when no source is injected.
- `add()` now captures `now = self.clock.now()` and uses that for both `created_at` and `run_at`.
- `ready()` now uses `self.clock.now()` and returns a deterministic ordering by sorting on:
  - priority descending
  - run_at ascending
  - created_at ascending
  - task id ascending
- `schedule_retry()` now uses `self.random_source.random()` for jitter and `self.clock.now()` for retry scheduling.
- Retry jitter was preserved; it is now deterministic whenever an injected random source is provided.

Verification run
- Command: `uv run --with pytest python -m pytest tests`
- Working directory: `/workspace/in/flakyqueue`
- Result: `4 passed in 0.01s`

Notes
- No test files were modified.
- No sleeps, test weakening, fixture-id hard-coding, or third-party dependencies were added.

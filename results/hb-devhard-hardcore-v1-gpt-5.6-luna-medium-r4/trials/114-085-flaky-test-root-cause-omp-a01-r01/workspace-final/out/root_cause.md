# Flaky test root cause

## Flaky behavior

The scheduler accepted injected `clock` and `random_source` objects, but the implementation did not consistently use them. Adding tasks and checking readiness called the process-global `time.time()`, and retry scheduling used both process-global time and `random.random()`. Therefore fake-clock tests observed wall-clock timestamps, and retry jitter varied independently of the supplied random sequence. `ready()` also shuffled eligible tasks with the global random generator before sorting only by priority. Equal-priority tasks consequently retained a random order.

## Root cause

`Scheduler` had dependency-injection fields that were effectively unused in `add`, `ready`, and `schedule_retry`. The ready queue's sort key omitted a deterministic tie-breaker, while the preceding global shuffle introduced nondeterminism. These are production-code defects, not test defects.

## Fix

- Use `self.clock.now()` for task creation, readiness cutoffs, and retry due times.
- Use the injected `random_source.random()` for retry jitter, defaulting to the standard `random` module only when no source is supplied.
- Remove the ready-list shuffle and sort by descending priority followed by task ID, making equal-priority ordering deterministic without removing retry jitter.
- Capture one clock reading in `add` so `created_at` and `run_at` are identical under both real and fake clocks.

## Verification

The requested source path was not mounted in this environment; its project is available as `/workspace/in/flakyqueue` and output as `/workspace/out`. Running the requested command there was attempted with `python -m pytest tests`, but `python` is not installed. The equivalent `python3 -m pytest tests` was also attempted and could not start because this environment has no `pytest` module.

I ran a direct deterministic contract check with the repository's fake-clock and fake-random behavior, covering:

- stable ordering across repeated `ready()` calls (`task-c`, `task-a`, `task-b`),
- injected clock values for task timestamps,
- injected retry jitter and exact retry due time (`210.25`), and
- readiness transition exactly at the injected retry `run_at` time.

That check printed `all scheduler contract checks passed`. `python3 -m compileall -q flakyqueue` also completed successfully.

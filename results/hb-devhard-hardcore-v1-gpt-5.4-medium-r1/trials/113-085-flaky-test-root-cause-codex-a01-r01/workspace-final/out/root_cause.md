Flaky behavior

The pytest failures came from production nondeterminism in `Scheduler`, not from unstable tests. The symptoms were:

- `add()` ignored the injected clock and stamped tasks with wall-clock time.
- `ready()` ignored the injected clock and randomized ready-task order on every call.
- `schedule_retry()` ignored the injected random source and wall clock, so retry `run_at` values varied by environment and timing.

Root cause

`flakyqueue/scheduler.py` accepted `clock` and `random_source` dependencies but still called the global `time.time()`, `random.random()`, and `random.shuffle()` functions directly. That broke determinism under test and in any production usage that injects a fake or controlled clock/random source.

The ordering bug was specifically caused by shuffling all ready tasks before sorting only by priority. For equal-priority tasks, the shuffle outcome leaked into the final result, so repeated `ready()` calls could return different orders for the same underlying queue state.

Fix

I changed the implementation to:

- use `self.clock.now()` in `add()`, `ready()`, and `schedule_retry()`
- default `random_source` to the module-level `random` object when none is injected
- use `self.random_source.random()` for retry jitter
- remove shuffle-based ordering and sort ready tasks deterministically by `(-priority, run_at, id)`

This preserves retry jitter while making it deterministic whenever a deterministic random source is injected.

Verification

I ran:

- `python3 -m pytest tests`

Result:

- `4 passed in 0.02s`

I also ran a direct Python check against the patched scheduler to confirm:

- equal-priority tasks return in stable order: `['task-c', 'task-a', 'task-b']`
- injected retry jitter is honored exactly: `run_at == 1010.25`
- a retried task does not become ready until the injected clock reaches its scheduled `run_at`

Note on output path

The requested host path under `<HOME>/.../workspace/out/root_cause.md` is not writable from this container because `/Users` is mounted read-only here. I wrote this report to the mounted workspace output path instead:

- `/workspace/out/root_cause.md`

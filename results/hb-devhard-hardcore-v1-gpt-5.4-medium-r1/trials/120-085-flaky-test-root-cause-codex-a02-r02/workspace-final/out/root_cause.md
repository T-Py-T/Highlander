Flaky behavior
==============

The scheduler had two sources of production nondeterminism:

1. `ready()` shuffled the ready-task list before sorting only by priority. For tasks with equal priority, the final order depended on the random shuffle result, so repeated calls could return different orders for the same queue contents.
2. `add()`, `ready()`, and `schedule_retry()` ignored the injected clock, and `schedule_retry()` ignored the injected random source. They used global `time.time()` and `random.random()` instead. That made retry timing and readiness depend on wall clock and process-global randomness even when tests or callers supplied deterministic fakes.

Root cause
==========

The implementation accepted injectable dependencies (`clock`, `random_source`) but did not actually use them in the scheduling paths that determine task ordering and retry timing.

In particular:

- `add()` stamped tasks with `time.time()` instead of `clock.now()`.
- `ready()` filtered with `time.time()` and then called `random.shuffle(...)`, which introduced unstable ordering for equal-priority tasks.
- `schedule_retry()` used `random.random()` and `time.time()` instead of the injected sources.

Because equal-priority tasks were shuffled and then sorted only on `priority`, Python's stable sort preserved a random pre-sort order for ties. That is the direct cause of the flaky ordering failures.

Fix
===

I updated `flakyqueue/scheduler.py` to:

- default `random_source` to the `random` module only when no source is injected,
- route all current-time reads through `clock.now()`,
- route retry jitter through `random_source.random()`,
- remove shuffle-based ordering and replace it with an explicit deterministic sort key:
  `(-priority, run_at, created_at, id)`.

This preserves priority ordering while making equal-priority ties deterministic when a clock/random source is injected.

Verification
============

Implementation checks run:

- `python3 -m compileall flakyqueue`
- a direct `python3` verification script that executed the same assertions as:
  - `tests/test_scheduler.py`
  - `tests/test_retry_order.py`

Those assertions passed after the change.

Environment limitation:

- I could not run the exact requested command `python -m pytest tests` in this container because:
  - `python` is not installed (`python3` is available at `/usr/bin/python3`)
  - `pytest` is not installed
  - `pip`, `pip3`, and `ensurepip` are also unavailable here

If you run the patched repo in an environment that has `python` and `pytest`, the intended verification command is:

`python -m pytest tests`

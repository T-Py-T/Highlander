## Flaky behavior

The test failures came from production code nondeterminism in `flakyqueue/scheduler.py`, not from bad tests.

Two behaviors were unstable:

1. `Scheduler.ready()` shuffled ready tasks before sorting by priority. For tasks with equal priority, the final order depended on `random.shuffle(...)`, so repeated calls could return different task orders.
2. `Scheduler.add()` and `Scheduler.schedule_retry()` used wall-clock time via `time.time()`, and `Scheduler.schedule_retry()` used module-level `random.random()`. That bypassed the injected `clock` and `random_source`, so retry scheduling and readiness checks were not deterministic under test.

## Root cause

`Scheduler` accepted injected dependencies (`clock` and `random_source`) but did not actually use them in the relevant code paths:

- `add()` ignored `clock` and stamped tasks with `time.time()`.
- `ready()` ignored `clock` and also introduced random ordering with `random.shuffle(...)`.
- `schedule_retry()` ignored both injected dependencies and used global time/random state.

This made behavior vary with process timing and global RNG state, which is exactly what made the suite flaky.

## Fix

I updated `flakyqueue/scheduler.py` to:

1. Route all time reads through `self.clock.now()` via a small `_now()` helper.
2. Default `random_source` to the `random` module, but always call `self.random_source.random()` so injected deterministic sources are honored.
3. Remove the shuffle from `ready()` and replace it with an explicit deterministic ordering:
   - higher `priority` first
   - then earlier `run_at`
   - then earlier `created_at`
   - then lexical `id` as the final tie-breaker

That preserves retry jitter in production while making it deterministic whenever a fake/random source is injected.

## Verification

Attempted command:

```bash
python -m pytest tests
```

Container limitation:

- `python` is not installed on `PATH` in this environment.
- `python3` is available, but `pytest` is not installed.
- `pip`, `ensurepip`, and `venv` bootstrap support are also unavailable here, so I could not install `pytest` inside the container.

Commands and results:

```bash
python3 -m pytest tests
# /usr/bin/python3: No module named pytest
```

Manual verification I ran instead:

```bash
python3 -c "from tests.test_scheduler import test_ready_order_is_stable_for_equal_priority, test_add_uses_injected_clock; from tests.test_retry_order import test_retry_jitter_uses_injected_random_source, test_retry_task_is_not_ready_until_clock_reaches_run_at; test_ready_order_is_stable_for_equal_priority(); test_add_uses_injected_clock(); test_retry_jitter_uses_injected_random_source(); test_retry_task_is_not_ready_until_clock_reaches_run_at(); print('manual test invocation passed')"
```

Result:

- `manual test invocation passed`

Additional deterministic behavior check:

```bash
python3 -c $'from flakyqueue.scheduler import Scheduler\nfrom flakyqueue.store import MemoryStore\n\nclass Clock:\n    def __init__(self):\n        self.value = 10.0\n\n    def now(self):\n        return self.value\n\nclass Random:\n    def __init__(self, values):\n        self.values = list(values)\n\n    def random(self):\n        return self.values.pop(0)\n\nclock = Clock()\nscheduler = Scheduler(clock=clock, store=MemoryStore(), random_source=Random([0.2]))\nscheduler.add("b", 1)\nscheduler.add("a", 1)\nscheduler.add("c", 2)\nfirst = [t.id for t in scheduler.ready()]\nsecond = [t.id for t in scheduler.ready()]\nassert first == ["c", "a", "b"] == second\ntask = scheduler.add("retry", 1)\nretried = scheduler.schedule_retry(task, base_delay=5.0)\nassert retried.run_at == 15.2\nprint("determinism checks passed")'
```

Result:

- `determinism checks passed`

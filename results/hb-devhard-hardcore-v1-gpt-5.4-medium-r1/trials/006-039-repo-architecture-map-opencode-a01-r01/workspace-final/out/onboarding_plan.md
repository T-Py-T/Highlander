# minisvc Onboarding Plan

## Read Order

1. `README.md` to learn the intended behavior and note that code is authoritative.
2. `pyproject.toml` to find the packaged CLI entry point.
3. `minisvc/cli.py` for the simplest real runtime path.
4. `minisvc/config.py` and `minisvc/storage/repo.py` for configuration and persistence.
5. `minisvc/api/routes.py` and `minisvc/api/handlers.py` for request flow.
6. `minisvc/models.py` and `minisvc/audit.py` for shared data structures.

Active runtime code is in the modules above. `minisvc/api/__init__.py` and `minisvc/storage/__init__.py` are package markers, and `minisvc/__init__.py` is a minimal export file rather than business logic.

## Local Run And Test Commands

Run from the repository root:

```bash
python -m minisvc.cli
MINISVC_DB=/tmp/minisvc.sqlite python -m minisvc.cli
python -m compileall minisvc
```

There is no in-repo HTTP server bootstrap or automated test suite. For a quick handler smoke test:

```bash
python - <<'PY'
from minisvc.api.handlers import create_order
from minisvc.storage.repo import OrderRepository

repo = OrderRepository('/tmp/minisvc-smoke.sqlite')
repo.init_schema()
print(create_order({'order_id': 'o-1', 'customer': 'Taylor', 'total_cents': '1234'}, repo))
PY
```

## First Breakpoint Or Trace Point

Start at `minisvc/api/handlers.py:create_order` on the `repo.save(order)` line.

Why this spot:

- It sits on the main write path.
- You can inspect payload parsing, `Order` construction, and the transition into SQLite persistence.
- It quickly reveals that readonly mode and retry behavior are not enforced.

## Two Safe First Changes

1. Add explicit request validation in `minisvc.api.handlers:create_order` so missing fields and bad `total_cents` values return stable errors instead of raw exceptions.
2. Wire `Settings.readonly` into the write path, either by checking it before `repo.save(order)` or by enforcing it in `OrderRepository.save`.

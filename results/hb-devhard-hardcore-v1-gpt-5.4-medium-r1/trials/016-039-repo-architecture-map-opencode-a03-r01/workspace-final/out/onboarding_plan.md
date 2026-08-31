# minisvc Onboarding Plan

## Read Order

1. `README.md` to understand the intended shape of the service and note that some design notes are stale.
2. `pyproject.toml` to see the packaged CLI entry point.
3. `minisvc/cli.py` to understand the only complete startup path in code.
4. `minisvc/config.py` and `minisvc/storage/repo.py` to learn configuration and persistence.
5. `minisvc/api/routes.py` and `minisvc/api/handlers.py` to understand request wiring and business behavior.
6. `minisvc/models.py` and `minisvc/audit.py` last, because they are simple support modules.

Active runtime code: `cli.py`, `config.py`, `storage/repo.py`, `api/routes.py`, `api/handlers.py`, `models.py`, `audit.py`.

Not business logic: `minisvc/api/__init__.py`, `minisvc/storage/__init__.py`, and the near-empty `minisvc/__init__.py` export file.

## Local Run Commands

Run the CLI bootstrap:

```bash
PYTHONPATH=. python -m minisvc.cli
```

Run with an explicit database path:

```bash
MINISVC_DB=/tmp/minisvc-orders.sqlite PYTHONPATH=. python -m minisvc.cli
```

There are no test files in the fixture repository. Use a small manual smoke check for the handler path:

```bash
PYTHONPATH=. python - <<'PY'
from minisvc.storage.repo import OrderRepository
from minisvc.api.handlers import create_order, get_order

repo = OrderRepository('/tmp/minisvc-orders.sqlite')
repo.init_schema()
print(create_order({'order_id': 'o-1', 'customer': 'Taylor', 'total_cents': '1250'}, repo))
print(get_order('o-1', repo))
PY
```

## First Breakpoint Or Trace Point

Set the first breakpoint in `minisvc/api/handlers.py:create_order` on the line just before `repo.save(order)`.

Why this point:

- It shows the raw payload-to-model conversion.
- It lets you inspect whether `total_cents` parsing succeeded.
- It is the narrowest point before persistence and before the response event is generated.

If you prefer tracing storage issues, the next best trace point is `minisvc/storage/repo.py:save` at the `conn.execute(...)` call.

## Two Safe First Changes

1. Add explicit request validation in `create_order` so missing keys and bad `total_cents` values become clear error responses instead of uncaught exceptions.
2. Enforce `Settings.readonly` on write paths, starting with `create_order` and optionally duplicating the guard in `OrderRepository.save` for defense in depth.

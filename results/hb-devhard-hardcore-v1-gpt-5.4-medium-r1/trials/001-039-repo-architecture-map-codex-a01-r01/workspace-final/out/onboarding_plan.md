# minisvc Onboarding Plan

## What To Read First

1. `README.md`
   Use it as context only; the older design notes are not fully implemented.
2. `pyproject.toml`
   Confirms the console entry point `minisvc.cli:main`.
3. `minisvc/cli.py`
   Shows the simplest end-to-end bootstrap path.
4. `minisvc/config.py`
   Explains the runtime inputs from the environment.
5. `minisvc/storage/repo.py`
   Shows the real persistence contract and schema.
6. `minisvc/api/handlers.py`
   Covers the main business behavior for create and read.
7. `minisvc/api/routes.py`
   Explains how handlers are exposed to an HTTP app.
8. `minisvc/audit.py` and `minisvc/models.py`
   Small supporting modules used by the handlers.

Treat `minisvc/api/__init__.py` and `minisvc/storage/__init__.py` as package markers, not runtime logic. `minisvc/__init__.py` is also dead-simple metadata (`__all__`) rather than business behavior.

## Local Run And Test Commands

From the fixture repo root:

```sh
cd /workspace/in/repo
python -m minisvc.cli
MINISVC_DB=/tmp/minisvc.sqlite python -m minisvc.cli
python - <<'PY'
from minisvc.api.handlers import create_order, get_order
from minisvc.storage.repo import OrderRepository

repo = OrderRepository('/tmp/minisvc-dev.sqlite')
repo.init_schema()
print(create_order({'order_id': 'o-1', 'customer': 'Taylor', 'total_cents': '1250'}, repo))
print(get_order('o-1', repo))
PY
```

There is no test suite in the fixture repository, so the quickest validation path is direct execution through the CLI and handlers.

## First Debugging Point

Start at `minisvc.api.handlers:create_order` on the `repo.save(order)` line. That point sits at the boundary between payload parsing, domain construction, and persistence, so it exposes the most useful state with minimal setup.

If you prefer tracing the bootstrap path first, set a breakpoint at `minisvc.cli:main` before `repo.init_schema()`.

## Two Safe First Changes

1. Add explicit request validation and stable error responses in `minisvc/api/handlers.py` without changing the storage schema.
2. Enforce `MINISVC_READONLY` in the write path, either in `create_order` before `repo.save(order)` or inside `OrderRepository.save`.

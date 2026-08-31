# minisvc onboarding plan

## Goal for day 1
Understand the two real runtime surfaces (`minisvc.cli:main` and `minisvc.api.routes:register_routes`), then trace how an order moves from payload to SQLite row and back.

## Read order
1. `README.md`
   - Quick context plus examples of stale design notes that you should verify against code.
2. `pyproject.toml`
   - Confirms the console entry point `minisvc.cli:main`.
3. `minisvc/cli.py`
   - Best top-down starting point for runtime bootstrap.
4. `minisvc/config.py`
   - Shows the only environment variables and the unused `readonly` setting.
5. `minisvc/storage/repo.py`
   - Core persistence behavior and schema shape.
6. `minisvc/api/handlers.py`
   - Main business flow for create/read requests.
7. `minisvc/api/routes.py`
   - Thin adapter layer that wires handlers to an app object.
8. `minisvc/audit.py` and `minisvc/models.py`
   - Small supporting pieces used by handlers.

## Files to treat as non-runtime or dead-simple
- `minisvc/__init__.py`: package marker plus `__all__`; not business logic.
- `minisvc/api/__init__.py`: effectively empty package marker.
- `minisvc/storage/__init__.py`: effectively empty package marker.

## Local run commands
Run the CLI bootstrap:
```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/in/repo python3 -c 'from minisvc.cli import main; raise SystemExit(main())'
```

Run a smoke test for create/read behavior without modifying repository code:
```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/in/repo python3 - <<'PY'
from pathlib import Path
from minisvc.api.handlers import create_order, get_order
from minisvc.storage.repo import OrderRepository

db = '/tmp/minisvc-smoke.sqlite'
Path(db).unlink(missing_ok=True)
repo = OrderRepository(db)
repo.init_schema()
print(create_order({'order_id': 'demo-1', 'customer': 'Taylor', 'total_cents': '2500'}, repo))
print(get_order('demo-1', repo))
PY
```

There are no repository-provided automated tests in this fixture, so the smoke script above is the fastest executable check.

## First debugging breakpoint or trace point
Start at `minisvc.api.handlers:create_order` on the line where `Order(...)` is built.
Why here:
- you can inspect raw payload assumptions
- you immediately see type coercion for `total_cents`
- the next step leads into `OrderRepository.save`, the main persistence boundary

If you prefer storage-first tracing, the second breakpoint should be `minisvc.storage.repo:save` before `conn.execute(...)`.

## Two safe first changes
1. Add explicit input validation in `minisvc/api/handlers.py`
   - Return structured bad-request responses for missing keys or invalid `total_cents`.
   - Safe because it is localized to handler behavior and does not require schema changes.
2. Enforce readonly mode before writes
   - Thread `Settings` into the write path and block `create_order` or `OrderRepository.save` when `MINISVC_READONLY=1`.
   - Safe because the repository already exposes a single save boundary and the config flag already exists.

## What to keep in mind
- The README contains intentionally stale claims; trust code over docs when they diverge.
- The only durable business storage is the `orders` table in SQLite.
- Audit data is currently response metadata, not persisted history.
- The app integration contract is implicit; `register_routes()` expects an app object with `.post()` and `.get()` methods.

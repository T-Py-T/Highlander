# Onboarding plan

## Start with the active code, not the markers
Read these first:
1. `README.md` for intent and known doc drift.
2. `pyproject.toml` to see the only packaged entry point: `minisvc.cli:main`.
3. `minisvc/cli.py` to understand startup and schema initialization.
4. `minisvc/config.py` to see runtime knobs: `MINISVC_DB`, `MINISVC_READONLY`.
5. `minisvc/storage/repo.py` to see the real persistence model and schema.
6. `minisvc/api/handlers.py` to see create/read behavior, validation gaps, and persistence calls.
7. `minisvc/api/routes.py` to see how an external HTTP adapter wires handlers.
8. `minisvc/audit.py` and `minisvc/models.py` last; both are small supporting files.

Do not spend time on these early:
- `minisvc/__init__.py`
- `minisvc/api/__init__.py`
- `minisvc/storage/__init__.py`

Those are package markers, not business logic.

## Local run commands
From the repository root:

```bash
python3 -c "from minisvc.cli import main; raise SystemExit(main())"
```

That is the most direct local startup command. `python3 -m minisvc.cli` only imports the module because `cli.py` has no `if __name__ == "__main__":` block.

Use a disposable database path when you want a clean run:

```bash
MINISVC_DB=/tmp/minisvc-orders.sqlite python3 -c "from minisvc.cli import main; raise SystemExit(main())"
```

## Local smoke test command
There is no test suite in this fixture. Use a direct smoke script against the real handlers and repository:

```bash
python3 - <<'PY'
import sqlite3
import tempfile
from pathlib import Path
from minisvc.storage.repo import OrderRepository
from minisvc.api.handlers import create_order, get_order

tmpdir = tempfile.TemporaryDirectory()
db = str(Path(tmpdir.name) / 'orders.sqlite')
repo = OrderRepository(db)
repo.init_schema()
print(create_order({'order_id': 'o-1', 'customer': 'Taylor', 'total_cents': '42'}, repo))
print(get_order('o-1', repo))
with sqlite3.connect(db) as conn:
    print(conn.execute("select order_id, customer, total_cents from orders").fetchall())
PY
```

## First breakpoint or trace point
Set your first breakpoint at `minisvc/api/handlers.py:create_order`.

Why there:
- It is the narrowest point where request data becomes an `Order`.
- You can inspect payload assumptions, `int()` coercion, repository calls, and the inline audit event in one stop.
- Most near-term bugs will show up here before they spread into framework glue.

If you prefer tracing over breakpoints, log the payload and the `repo.save(order)` call boundary in `create_order` while using a temporary SQLite file.

## Runtime flow to internalize
1. Console entry point calls `minisvc.cli:main`.
2. `main` loads settings from environment.
3. `main` instantiates `OrderRepository` and initializes schema.
4. External HTTP integration calls `minisvc.api.routes:register_routes(app, repo)`.
5. POST `/orders` reaches `create_order`; GET `/orders/<order_id>` reaches `get_order`.
6. Repository methods open SQLite connections per operation.
7. Audit data is returned in responses only; it is not persisted.

## Two safe first changes
1. Add targeted request validation in `minisvc/api/handlers.py:create_order` so missing fields and non-integer totals return controlled errors instead of raw exceptions.
2. Add a small integration-style test file that exercises `OrderRepository.init_schema`, `create_order`, and `get_order` against a temporary SQLite database.

Both changes are low-risk, local, and teach the real runtime boundaries without redesigning the service.

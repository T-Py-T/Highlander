# minisvc onboarding plan

## Goal
Get to the point where you can run the bootstrap path, trace one order create flow, and tell live runtime code from package marker files.

## Read order
1. `README.md` — short product and stale design-note context.
2. `pyproject.toml` — confirms the console entry point `minisvc.cli:main`.
3. `minisvc/cli.py` — startup path and schema init.
4. `minisvc/config.py` — env-driven settings.
5. `minisvc/storage/repo.py` — real persistence logic.
6. `minisvc/api/handlers.py` — create/get behavior.
7. `minisvc/api/routes.py` — how the host app wires handlers.
8. `minisvc/audit.py` and `minisvc/models.py` — small support modules.

Treat these as active runtime code:
- `minisvc/cli.py`
- `minisvc/config.py`
- `minisvc/storage/repo.py`
- `minisvc/api/handlers.py`
- `minisvc/api/routes.py`
- `minisvc/audit.py`
- `minisvc/models.py`

Treat these as package markers or dead-simple packaging files, not business logic:
- `minisvc/__init__.py`
- `minisvc/api/__init__.py`
- `minisvc/storage/__init__.py`
- `pyproject.toml`

## Local run and smoke-check commands
From the repo root:

```bash
cd /workspace/in/repo
MINISVC_DB=/tmp/minisvc.sqlite python3 -c "from minisvc.cli import main; raise SystemExit(main())"
python3 -m compileall minisvc
python3 - <<'PY'
from minisvc.storage.repo import OrderRepository
from minisvc.api.handlers import create_order, get_order
repo = OrderRepository('/tmp/minisvc.sqlite')
repo.init_schema()
print(create_order({'order_id': 'o-1', 'customer': 'Taylor', 'total_cents': 500}, repo))
print(get_order('o-1', repo))
PY
```

There are no repository tests in this fixture, so the last snippet is the quickest end-to-end smoke check.

## First breakpoint or trace point
Start at `minisvc/api/handlers.py:create_order`, right before `repo.save(order)`.

Why this spot:
- you can inspect the raw payload
- you can see type coercion into `Order`
- you can step into `minisvc/storage/repo.py:save`
- you can confirm that audit data is built after the write and not stored anywhere

## Two safe first changes
1. Add focused tests or a smoke harness for `load_settings()`, `create_order()`, and duplicate-order behavior.
2. Tighten docs to match code, especially around readonly mode, retry behavior, and audit persistence.

## What to keep in mind
- The CLI path creates the schema; the HTTP path does not.
- `MINISVC_READONLY` is parsed but not enforced.
- Audit data is returned in responses only.
- SQLite path defaults to a relative file: `orders.sqlite`.

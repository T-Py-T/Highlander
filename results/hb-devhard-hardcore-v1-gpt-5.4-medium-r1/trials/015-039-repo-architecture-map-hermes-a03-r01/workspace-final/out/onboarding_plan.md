# minisvc onboarding plan

## Goal for day 1
Understand the real runtime path from config -> handler -> repository -> SQLite, and ignore package marker files that do not contain behavior.

## Recommended read order
1. `README.md`
   - Read it first, but treat it as a hypothesis because it explicitly says code is authoritative when docs disagree.
2. `pyproject.toml`
   - Find the CLI entry point: `minisvc.cli:main`.
3. Active runtime code:
   - `minisvc/cli.py`
   - `minisvc/config.py`
   - `minisvc/api/routes.py`
   - `minisvc/api/handlers.py`
   - `minisvc/storage/repo.py`
   - `minisvc/audit.py`
   - `minisvc/models.py`
4. De-prioritize dead-simple/package marker files:
   - `minisvc/__init__.py`
   - `minisvc/api/__init__.py`
   - `minisvc/storage/__init__.py`

## Local run/test commands
From the repository root, use the script entry point function directly:

```bash
PYTHONPATH=/workspace/in/repo python3 - <<'PY'
from minisvc.cli import main
raise SystemExit(main())
PY
```

Set an explicit database path if you do not want `orders.sqlite` in the current directory:

```bash
MINISVC_DB=/tmp/minisvc.sqlite PYTHONPATH=/workspace/in/repo python3 - <<'PY'
from minisvc.cli import main
raise SystemExit(main())
PY
```

Quick route/handler smoke test without adding a framework dependency:

```bash
PYTHONPATH=/workspace/in/repo python3 - <<'PY'
from minisvc.api.routes import register_routes
from minisvc.storage.repo import OrderRepository

class FakeApp:
    def __init__(self):
        self.routes = {}
    def post(self, path, handler):
        self.routes[('POST', path)] = handler
    def get(self, path, handler):
        self.routes[('GET', path)] = handler

repo = OrderRepository('/tmp/minisvc-smoke.sqlite')
repo.init_schema()
app = FakeApp()
register_routes(app, repo)
print(app.routes[('POST', '/orders')]({'order_id': 'o1', 'customer': 'Taylor', 'total_cents': '1500'}))
print(app.routes[('GET', '/orders/<order_id>')]('o1'))
PY
```

Tests
- No automated tests are present in this fixture repository, so the smoke commands above are the practical starting point.

## First debugging breakpoint or trace point
Start at `minisvc/api/handlers.py:create_order` on the `repo.save(order)` line.
Why:
- it sits at the boundary between unvalidated input and persistence
- it exposes the most important mismatch with the README: no readonly enforcement, no retry loop, no error translation
- you can inspect the fully built `Order` and the active repository path before the write happens

Secondary trace point: `minisvc/storage/repo.py:save` to inspect the exact SQLite insert.

## Two safe first changes
1. Add explicit input validation in `create_order`.
   - Convert raw `KeyError`/`ValueError` cases into a predictable error payload or a small typed validation helper.
   - This is localized and easy to verify with the smoke harness.
2. Enforce readonly mode before writes.
   - Thread `Settings.readonly` into the write path or guard writes in the handler/repository.
   - This directly resolves one of the main doc/code mismatches.

## Things to keep in mind
- The repo contains route registration, not a full HTTP server.
- Audit output is only an in-memory dict today; nothing durable is written for audit history.
- The package marker `__init__.py` files are not where behavior lives.

# minisvc onboarding plan

## Goal for day 1
Understand the only real runtime path: order requests become `Order` objects in `minisvc/api/handlers.py`, then are persisted by `minisvc/storage/repo.py`.

## Read order
1. `README.md`
   - Read it for service intent, but treat the older design notes as potentially stale.
2. `pyproject.toml`
   - Confirms the CLI entry point `minisvc.cli:main`.
3. `minisvc/cli.py`
   - Shows startup, config loading, repository creation, and schema initialization.
4. `minisvc/config.py`
   - Shows environment variables and the unused `readonly` setting.
5. `minisvc/api/routes.py`
   - Shows the HTTP surface and how handlers are wired.
6. `minisvc/api/handlers.py`
   - Primary business logic for create/read order flows.
7. `minisvc/storage/repo.py`
   - SQLite schema and persistence details.
8. `minisvc/audit.py` and `minisvc/models.py`
   - Small support modules.

Files to de-prioritize because they are package markers or dead-simple exports, not active runtime logic:
- `minisvc/__init__.py`
- `minisvc/api/__init__.py`
- `minisvc/storage/__init__.py`

## Local run commands
From the fixture repo root:

```bash
cd /workspace/in/repo
PYTHONPATH=/workspace/in/repo python3 - <<'PY'
from minisvc.cli import main
raise SystemExit(main())
PY
```

Smoke-test the handler flow with an isolated temp database:

```bash
cd /workspace/in/repo
PYTHONPATH=/workspace/in/repo python3 - <<'PY'
from minisvc.storage.repo import OrderRepository
from minisvc.api.handlers import create_order, get_order
import tempfile, os
fd, path = tempfile.mkstemp(suffix='.sqlite')
os.close(fd)
repo = OrderRepository(path)
repo.init_schema()
print(create_order({'order_id':'o1','customer':'Ada','total_cents':'1234'}, repo))
print(get_order('o1', repo))
os.unlink(path)
PY
```

## First debugging breakpoint or trace point
Start at `minisvc/api/handlers.py:create_order` right before `repo.save(order)`.
Why this point first:
- the payload has already been translated into an `Order`
- you can inspect validation assumptions
- you can step into `OrderRepository.save` to see the exact SQL write path
- it is the fastest place to confirm that `readonly` is not enforced

If you prefer trace logging over breakpoints, add a temporary print/log around `create_order` inputs and around `OrderRepository.save` parameters.

## Runtime flow to keep in mind
- CLI startup is the only built-in schema initialization path.
- HTTP route registration does not create the repository or initialize the database for you.
- Audit data is returned in responses but is not stored anywhere durable.

## Two safe first changes
1. Add explicit payload validation in `minisvc/api/handlers.py:create_order`
   - Safely convert missing-field and bad-integer cases into controlled error responses or typed exceptions.
   - This is localized and easy to cover with small tests.
2. Implement actual read-only enforcement
   - Thread `Settings.readonly` into the write path and block `repo.save(order)` when enabled.
   - This closes a documented/code mismatch without changing the overall service shape.

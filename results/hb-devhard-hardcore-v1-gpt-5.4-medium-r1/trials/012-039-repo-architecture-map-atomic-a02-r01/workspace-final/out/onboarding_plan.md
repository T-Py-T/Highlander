# minisvc onboarding plan

## What to read first
1. `README.md` — short project shape and old design claims.
2. `minisvc/cli.py` — simplest real entry point.
3. `minisvc/config.py` — runtime settings and env keys.
4. `minisvc/storage/repo.py` — actual persistence behavior.
5. `minisvc/api/handlers.py` — request-to-storage flow.
6. `minisvc/api/routes.py` — how HTTP hooks are wired.
7. `minisvc/audit.py` and `minisvc/models.py` — small support code.
8. `minisvc/__init__.py`, `minisvc/api/__init__.py`, `minisvc/storage/__init__.py` — package markers only; skim last.

## Active runtime code vs simple files
### Active runtime code
- `minisvc/cli.py`
- `minisvc/config.py`
- `minisvc/storage/repo.py`
- `minisvc/api/handlers.py`
- `minisvc/api/routes.py`
- `minisvc/audit.py`
- `minisvc/models.py`

### Simple or non-runtime-heavy files
- `README.md` — docs only
- `pyproject.toml` — packaging and console-script entry
- `minisvc/__init__.py` — tiny export file
- `minisvc/api/__init__.py` — package marker
- `minisvc/storage/__init__.py` — package marker

## Local run commands
Use a temp DB path so you do not create data in the repo root.

### CLI smoke run
```bash
cd /workspace/in/repo
PYTHONDONTWRITEBYTECODE=1 MINISVC_DB=/tmp/minisvc.sqlite python3 - <<'PY'
from minisvc.cli import main
raise SystemExit(main())
PY
```

### Manual create/read handler smoke run
```bash
cd /workspace/in/repo
PYTHONDONTWRITEBYTECODE=1 MINISVC_DB=/tmp/minisvc.sqlite python3 - <<'PY'
from minisvc.storage.repo import OrderRepository
from minisvc.api.handlers import create_order, get_order

repo = OrderRepository('/tmp/minisvc.sqlite')
repo.init_schema()
print(create_order({'order_id': 'o-1', 'customer': 'Ada', 'total_cents': '1250'}, repo))
print(get_order('o-1', repo))
PY
```

## First breakpoint or trace point
Start at `minisvc/api/handlers.py:create_order`.
- It is the narrow point where request data turns into an `Order`, storage write, and audit event.
- If you prefer print tracing, log right before `repo.save(order)` and right after `order_event(order, "created")`.
- If you use a debugger, step next into `minisvc/storage/repo.py:OrderRepository.save`.

## Two safe first changes
1. **Add input validation with clean errors in `create_order`**
   - low blast radius
   - easy to test by calling the handler with bad payloads
2. **Enforce or remove the unused readonly setting**
   - either check `Settings.readonly` before writes or delete the dead flag and update docs
   - good first task because the gap is small and well bounded

## What to keep in mind
- The repo does not include a full HTTP server bootstrap.
- README design notes are not fully true; trust the code over the docs.
- There is no durable audit store in the current implementation.

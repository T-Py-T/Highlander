# New engineer onboarding plan

## What to read first
1. `README.md` — read the repo promise, but expect code to win where notes are old.
2. `pyproject.toml` — see the console entry point `minisvc.cli:main`.
3. `minisvc/cli.py` — shortest live startup path.
4. `minisvc/config.py` — runtime settings and env names.
5. `minisvc/storage/repo.py` — SQLite schema, writes, and reads.
6. `minisvc/api/handlers.py` — business flow for create/read.
7. `minisvc/api/routes.py` — adapter wiring.
8. `minisvc/audit.py` and `minisvc/models.py` — small support code.

## Active runtime code vs simple files
### Active runtime code
- `minisvc/cli.py`
- `minisvc/config.py`
- `minisvc/storage/repo.py`
- `minisvc/api/handlers.py`
- `minisvc/api/routes.py`
- `minisvc/audit.py`
- `minisvc/models.py`

### Package marker or dead-simple files
- `minisvc/__init__.py` — export stub only
- `minisvc/api/__init__.py` — empty package marker
- `minisvc/storage/__init__.py` — empty package marker

## Local run commands
From the repo root:
- Bootstrap the CLI path:
  - `python3 -c 'from minisvc.cli import main; raise SystemExit(main())'`
- Run with a chosen DB path:
  - `MINISVC_DB=/tmp/minisvc.sqlite python3 -c 'from minisvc.cli import main; raise SystemExit(main())'`
- Quick import sanity check:
  - `python3 -m compileall minisvc`
- Quick create/read trace in one process:
  - `python3 - <<'PY'
from minisvc.storage.repo import OrderRepository
from minisvc.api.handlers import create_order, get_order
repo = OrderRepository('/tmp/minisvc-dev.sqlite')
repo.init_schema()
print(create_order({'order_id': 'o1', 'customer': 'Ada', 'total_cents': 1200}, repo))
print(get_order('o1', repo))
PY`

## First breakpoint or trace point
Start at `minisvc/api/handlers.py:create_order`.
- It is the best first stop because it shows payload parsing, model creation, persistence, and audit-event creation in one short path.
- If you want lower-level storage detail, step next into `minisvc/storage/repo.py:save`.

## Two safe first changes
1. Add a small test or guard for readonly mode around `create_order` or `OrderRepository.save`.
   - Safe because the setting already exists in `config.py` but is not enforced.
2. Add input validation for `order_id`, `customer`, and `total_cents` in `create_order`.
   - Safe because current code already depends on those fields and fails hard on bad payloads.

## What to keep in mind
- The HTTP app object is outside this repo.
- Audit events are returned in responses, not stored.
- The README design notes do not match all current behavior, so check the code before you change anything.

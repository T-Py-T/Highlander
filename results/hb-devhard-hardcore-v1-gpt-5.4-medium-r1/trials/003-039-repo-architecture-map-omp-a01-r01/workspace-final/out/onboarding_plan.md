# minisvc onboarding plan

## What is runtime code vs simple package files
- Active runtime code: `minisvc/cli.py`, `minisvc/config.py`, `minisvc/models.py`, `minisvc/audit.py`, `minisvc/api/routes.py`, `minisvc/api/handlers.py`, `minisvc/storage/repo.py`.
- Not business logic: `minisvc/__init__.py` and `minisvc/storage/__init__.py` are empty package markers; `minisvc/api/__init__.py` only exports names.

## Recommended read order
1. `README.md` — short product intent plus the outdated design notes you should treat skeptically.
2. `pyproject.toml` — confirms the only console entry point: `minisvc.cli:main`.
3. `minisvc/cli.py` — startup path and schema bootstrap.
4. `minisvc/config.py` — env contract: `MINISVC_DB`, `MINISVC_READONLY`.
5. `minisvc/storage/repo.py` — the real persistence boundary.
6. `minisvc/api/routes.py` — how HTTP exposure is wired.
7. `minisvc/api/handlers.py` — request/response behavior, error surface, and missing policy enforcement.
8. `minisvc/audit.py` and `minisvc/models.py` — lightweight support code.

## Local run and test commands
```bash
cd /workspace/in/repo
PYTHONPATH=. python -m minisvc.cli
PYTHONPATH=. python - <<'PY'
from minisvc.storage.repo import OrderRepository
from minisvc.api.handlers import create_order, get_order
repo = OrderRepository('orders.sqlite')
repo.init_schema()
print(create_order({'order_id': 'demo-1', 'customer': 'Taylor', 'total_cents': '1500'}, repo))
print(get_order('demo-1', repo))
PY
```
Notes:
- Set `MINISVC_DB=/tmp/minisvc.sqlite` if you do not want the default `orders.sqlite` in the current directory.
- There is no test suite in the fixture repository; the handler smoke snippet is the fastest executable proof of behavior.

## First debugging breakpoint or trace point
- First breakpoint: `minisvc/api/handlers.py`, function `create_order`, on the `repo.save(order)` call.
  - Why: this is where request data becomes durable state, and it is also where readonly enforcement, retry logic, and DB failures would need to appear if implemented.
- First lightweight trace point if not using a debugger: print/log the incoming payload and the `Settings` loaded in `minisvc.cli:main` to confirm DB path and readonly mode assumptions.

## Two safe first changes
1. Add explicit input validation in `minisvc.api.handlers:create_order` so missing keys or non-integer `total_cents` become stable client-facing errors instead of raw exceptions.
2. Align docs to code or code to docs for readonly/audit behavior. Safest starting move: update documentation to state that readonly is currently unenforced and audit events are response-only until persistence is added.

## Early mental model
- The repository is tiny and layered: config -> cli/routes -> handlers -> repository -> SQLite.
- The docs overstate behavior. Trust the code first, especially for readonly, retries, and audit persistence.

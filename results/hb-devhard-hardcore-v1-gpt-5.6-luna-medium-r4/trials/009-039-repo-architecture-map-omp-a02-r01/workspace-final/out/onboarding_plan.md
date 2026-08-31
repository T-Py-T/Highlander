# minisvc onboarding plan

## Recommended read order

1. `README.md` — service scope and the three legacy claims that must be checked against code.
2. `pyproject.toml` — package metadata and the `minisvc` console-script target.
3. `minisvc/models.py` — the `Order` domain shape.
4. `minisvc/config.py` — environment names, defaults, and the currently unused readonly setting.
5. `minisvc/storage/repo.py` — SQLite schema and repository transaction boundaries.
6. `minisvc/api/handlers.py` — create/get behavior, coercion, and response shape.
7. `minisvc/api/routes.py` — adapter bindings and handler call graph.
8. `minisvc/cli.py` — runtime composition and startup sequence.
9. `minisvc/audit.py` — response event formatting; it is not durable audit storage.

The three `__init__.py` files are package markers (the root has a small `__all__` export); skip them as business logic.

## Local run and test commands

From the repository root:

```bash
python -m pip install -e .
MINISVC_DB=/tmp/minisvc-orders.sqlite minisvc
python -m compileall minisvc
```

There is no test suite or HTTP server implementation in this fixture. Exercise handlers with a small injected fake app/repository or a Python one-liner, for example:

```bash
python - <<'PY'
from minisvc.api.handlers import create_order, get_order
from minisvc.storage.repo import OrderRepository
repo = OrderRepository('/tmp/minisvc-orders.sqlite')
repo.init_schema()
print(create_order({'order_id': 'demo-1', 'customer': 'Ada', 'total_cents': '1250'}, repo))
print(get_order('demo-1', repo))
PY
```

## First debugging trace point

Set the first breakpoint at `minisvc.api.handlers:create_order`, line 6, then step into `OrderRepository.save` (`minisvc/storage/repo.py`, line 17). Inspect the constructed `Order`, the configured `database_path`, and the single SQLite insert. For startup issues, trace `minisvc.cli:main` line 8 through `load_settings` and line 10 through `init_schema`.

## Two safe first changes

1. Add focused validation around `create_order` that preserves the current valid response shape while converting missing/malformed fields into the adapter's explicit client-error response. Do not alter repository schema in the same change.
2. Add a repository-level read-only policy and tests for both `save` and `init_schema`, after deciding whether readonly startup may create a missing schema. Keep the policy in the active runtime modules (`config.py`, `cli.py`, `storage/repo.py`), not in package markers.

Do not assume the README's retry or durable-audit claims are implemented: the current code has one save attempt and transient response events only.

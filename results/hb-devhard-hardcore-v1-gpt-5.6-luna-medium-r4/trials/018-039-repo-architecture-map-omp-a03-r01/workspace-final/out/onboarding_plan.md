# minisvc onboarding plan

## Recommended read order

1. `README.md` and `pyproject.toml` — stated behavior and the `minisvc.cli:main` console entry point. Treat the README design notes as claims to verify, not as authority.
2. `minisvc/config.py` — `Settings` and environment parsing.
3. `minisvc/cli.py` — startup wiring and the actual process lifecycle.
4. `minisvc/models.py` — the small `Order` domain object.
5. `minisvc/storage/repo.py` — SQLite schema and repository boundaries.
6. `minisvc/api/routes.py`, then `minisvc/api/handlers.py` — HTTP binding and create/read behavior.
7. `minisvc/audit.py` — response event construction and its lack of persistence.

The three `__init__.py` files are package markers (the root one has a small `__all__` export list); they are not active request or storage logic.

## Run and smoke-test locally

From the repository root:

```bash
python -m pip install -e .
MINISVC_DB=/tmp/minisvc-onboarding.sqlite minisvc
```

The command creates the `orders` table if needed and prints readiness. It does not start an HTTP server. A direct handler smoke test can exercise the active path without a framework:

```bash
MINISVC_DB=/tmp/minisvc-onboarding.sqlite python - <<'PY'
from minisvc.api.handlers import create_order, get_order
from minisvc.storage.repo import OrderRepository

repo = OrderRepository("/tmp/minisvc-onboarding.sqlite")
repo.init_schema()
print(create_order({"order_id": "demo-1", "customer": "Ada", "total_cents": "1250"}, repo))
print(get_order("demo-1", repo))
PY
```

There are no test files or test dependency declarations in this fixture. Until a suite is added, use the smoke path above and manually exercise missing keys, invalid totals, duplicate IDs, and `MINISVC_READONLY=1` to observe current behavior.

## First debugging trace point

Set the first breakpoint at `minisvc.api.handlers.create_order` line 6. Trace payload extraction and `int()` conversion, then step into `OrderRepository.save` line 17 to observe the SQLite insert. For startup/configuration issues, use `minisvc.cli.main` line 8 and inspect `settings.readonly` versus the subsequent unconditional schema initialization.

## Safe first changes

1. Add focused request validation immediately before `Order(...)` in `create_order`, with explicit handling for missing keys, integer conversion, non-negative totals, and stable client-facing errors. Preserve the repository interface and add behavior tests for invalid and valid payloads.
2. Enforce readonly at the repository/application write boundary using the existing `Settings.readonly` value, while deciding explicitly whether schema creation is permitted in readonly mode. Add a test proving that a readonly create cannot insert a row.

Keep changes out of package marker files unless import/export behavior is intentionally being changed; the runtime seams are `load_settings`, `OrderRepository`, `register_routes`, and the two handlers.

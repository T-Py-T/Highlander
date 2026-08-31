# minisvc onboarding plan

## Recommended read order

1. `README.md` and `pyproject.toml` — stated intent and the `minisvc.cli:main` executable mapping. Treat the README design notes as claims to verify, not as behavior.
2. `minisvc/config.py` — runtime settings and defaults.
3. `minisvc/models.py` — the small `Order` data shape.
4. `minisvc/storage/repo.py` — actual SQLite schema and persistence semantics.
5. `minisvc/api/routes.py`, then `minisvc/api/handlers.py` — route wiring and request-to-storage flow.
6. `minisvc/audit.py` — response-only event construction and its limits.
7. `minisvc/cli.py` — how configuration and schema initialization are assembled at startup.

The three `__init__.py` files are package markers only: they are active for package discovery/import structure but contain no business logic. Focus debugging and changes on the modules above.

## Local run and test commands

From the repository root:

```bash
python -m minisvc.cli
```

The module currently defines `main` but does not invoke it under an `if __name__ == "__main__"` guard, so the installed script is the reliable CLI path:

```bash
python -m pip install -e .
MINISVC_DB=/tmp/minisvc-orders.sqlite minisvc
```

There is no test suite or test configuration in this fixture. For a smoke check after installation, verify the command prints `minisvc ready at ...` and creates the SQLite database/table. API behavior requires an external adapter object implementing `post` and `get`; call `register_routes(app, repo)` with a temporary database to exercise route registration and handlers.

## First debugging breakpoint / trace point

Set the first breakpoint at `minisvc.api.handlers.create_order`, line 6, for a `POST /orders` request. Inspect the payload before `Order` construction, then step into `OrderRepository.save` (line 17) and `order_event` (line 4). This covers validation, persistence, and the documented-but-not-durable audit behavior in one trace. For startup-only issues, use `minisvc.cli.main`, line 8, and inspect `settings.database_path` and `settings.readonly`.

## Safe first changes

1. Add focused input validation and stable client-facing error mapping around `create_order`; preserve the existing repository interface and avoid changing schema behavior in the same change.
2. Add an explicit readonly policy test and enforcement at the write boundary (`OrderRepository.save` or a clearly owned service policy), using `Settings.readonly` rather than adding a second configuration convention.

Both changes should be accompanied by tests once a test harness is introduced. Do not begin by editing package marker files; they are not runtime business logic.

# Onboarding Plan

## Read Order

1. Read `README.md` and `pyproject.toml` for the stated intent and console entry point; treat the README design notes as claims to verify.
2. Read `minisvc/config.py` and `minisvc/models.py` for runtime settings and the data shape.
3. Read `minisvc/storage/repo.py` to understand the actual SQLite schema and persistence behavior.
4. Read `minisvc/api/handlers.py`, then `minisvc/api/routes.py`, to follow HTTP input and response flow.
5. Read `minisvc/cli.py` for startup wiring, and `minisvc/audit.py` for response event construction.

`minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are package marker/dead-simple files, not active business logic. The active runtime code is the modules listed above.

## Run and Test

From the repository root:

```sh
python -m compileall minisvc
PYTHONPATH=. python -c 'from minisvc.cli import main; raise SystemExit(main())'
python -m pytest
```

The fixture has no test files, so `pytest` may report that no tests were collected. The CLI command creates `orders.sqlite` in the current directory unless `MINISVC_DB` is set.

## First Trace Point

Set the first breakpoint at `minisvc.api.handlers:create_order`, before `Order(...)` is constructed. Inspect the payload, then step through `OrderRepository.save` and `order_event`. For startup issues, begin at `minisvc.cli:main` line 8 and inspect the resulting `Settings`.

## Safe First Changes

- Add focused tests for `load_settings`, `create_order`, `get_order`, and repository round trips using a temporary SQLite path; this changes no production behavior.
- Add explicit payload validation that returns a defined client-error shape, while preserving valid-order behavior; do this before changing storage or retry semantics.

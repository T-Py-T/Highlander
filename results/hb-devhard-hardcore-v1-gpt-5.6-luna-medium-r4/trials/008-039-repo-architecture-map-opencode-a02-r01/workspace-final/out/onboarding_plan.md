# Onboarding Plan

## Read Order

1. Read `README.md` and `pyproject.toml` for the stated claims and console entry point, treating the code as authoritative.
2. Read `minisvc/cli.py` and `minisvc/config.py` to understand startup and environment behavior.
3. Read `minisvc/api/routes.py`, then `minisvc/api/handlers.py` for HTTP control flow.
4. Read `minisvc/models.py` and `minisvc/storage/repo.py` for the data model and SQLite boundary.
5. Read `minisvc/audit.py` to verify that events are constructed, not persisted.

The active runtime files are the modules above. `minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are package markers/exports and contain no business flow.

## Run and Test

From the repository root:

```sh
python -c 'from minisvc.cli import main; raise SystemExit(main())'
MINISVC_DB=/tmp/minisvc-orders.sqlite python -c 'from minisvc.cli import main; raise SystemExit(main())'
python -m pytest
```

The project declares the `minisvc = minisvc.cli:main` console script, but no test suite or HTTP server bootstrap is present in this fixture. Route tests can inject a minimal app and `OrderRepository` and call `register_routes` directly.

## First Trace Point

Set the first breakpoint at `minisvc.api.handlers:create_order`, then step into `OrderRepository.save` and inspect the SQLite insert. For startup issues, begin at `minisvc.cli:main` line 8 and inspect `Settings` before schema initialization.

## Safe First Changes

- Add focused validation around `create_order` that preserves the current valid payload contract while returning structured errors for missing keys and invalid `total_cents`.
- Add tests for `load_settings` defaults/overrides and repository create/read behavior using a temporary database; these changes are isolated and expose current behavior without changing production semantics.

Do not assume readonly, retries, or durable audit logging exist until those behaviors are explicitly implemented and tested.

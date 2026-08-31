# Onboarding Plan

## Recommended Read Order

1. Read `README.md` for the stated design claims and its warning that code is authoritative.
2. Read `pyproject.toml` to find the `minisvc.cli:main` console entry point.
3. Read `minisvc/cli.py` and `minisvc/config.py` for startup and environment behavior.
4. Read `minisvc/models.py`, then `minisvc/storage/repo.py` for the data model and SQLite boundary.
5. Read `minisvc/api/routes.py` and `minisvc/api/handlers.py` for HTTP wiring and request behavior.
6. Read `minisvc/audit.py` to verify that events are constructed in memory rather than persisted.

The active runtime code is in the seven modules above. The empty `minisvc/api/__init__.py` and `minisvc/storage/__init__.py` are package markers; `minisvc/__init__.py` only declares exports. None is a business-logic starting point.

## Local Run and Test

From the repository root:

```sh
python -m minisvc.cli
MINISVC_DB=/tmp/minisvc-orders.sqlite python -m minisvc.cli
python -m pytest
```

There are no test files or declared runtime dependencies in this fixture, and `python -m minisvc.cli` relies on Python's module execution behavior even though the packaged executable is the documented entry point. The CLI initializes the database and exits; it does not start an HTTP server.

## First Trace Point

Set the first breakpoint at `minisvc.api.handlers.create_order`, line 6. Trace payload key access and `int()` conversion, then step into `OrderRepository.save` at line 17 and inspect the SQL execution. For startup-only issues, begin at `minisvc.cli.main` line 8 and follow `load_settings`.

## Safe First Changes

- Add focused validation and tests around `create_order` without changing the repository schema: cover missing keys, invalid amounts, and a valid insert.
- Add an explicit readonly policy test and enforcement at the repository/write boundary, after confirming the desired behavior for direct repository callers as well as HTTP callers.

Avoid assuming the README's retry and durable-audit claims are implemented: the current code has neither.

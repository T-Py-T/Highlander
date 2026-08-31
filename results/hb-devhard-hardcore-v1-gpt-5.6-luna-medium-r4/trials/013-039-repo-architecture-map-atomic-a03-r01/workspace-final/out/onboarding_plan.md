# Onboarding plan

## Read order

1. Read `README.md` for stated behavior and its authority warning.
2. Read `pyproject.toml` to find the `minisvc.cli:main` console entry point.
3. Read `minisvc/config.py` and `minisvc/models.py` for settings and the data shape.
4. Trace `minisvc/cli.py` into `minisvc/storage/repo.py` for startup and SQLite behavior.
5. Trace `minisvc/api/routes.py` into `minisvc/api/handlers.py`, then `audit.py`.
6. Skip `__init__.py` files except to note they are package markers; they contain no runtime business logic.

## Run and test

From the repository root:

```sh
python -c 'from minisvc.cli import main; raise SystemExit(main())'
MINISVC_DB=/tmp/minisvc.sqlite python -c 'from minisvc.cli import main; raise SystemExit(main())'
python -m pytest
```

No test suite is included in the fixture, so the last command may report that no tests were collected.

## First trace point

Set a breakpoint in `minisvc.api.handlers:create_order` line 6 (or log the payload there), then step into `OrderRepository.save` line 17. This shows input conversion, persistence, and where exceptions escape.

## Safe first changes

1. Add focused tests around `load_settings` defaults and `OrderRepository.get/save` using a temporary SQLite path; this does not alter production behavior.
2. Add explicit payload validation in `create_order` with tests for missing fields and invalid `total_cents`, while preserving the current response contract for valid input.

Treat readonly enforcement, retries, and durable audit storage as separate reviewed changes because the current implementation does not provide them.

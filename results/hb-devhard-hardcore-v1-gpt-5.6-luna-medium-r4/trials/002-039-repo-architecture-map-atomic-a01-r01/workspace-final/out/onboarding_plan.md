# Onboarding plan

## Recommended read order

1. `README.md` and `pyproject.toml` for stated intent and the `minisvc.cli:main` console entry point.
2. `minisvc/cli.py` and `minisvc/config.py` for startup and environment settings.
3. `minisvc/api/routes.py`, then `minisvc/api/handlers.py` for HTTP wiring and use cases.
4. `minisvc/models.py`, `minisvc/storage/repo.py`, and `minisvc/audit.py` for the model, SQLite access, and response-only events.
5. Treat `minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` as package markers, not active runtime modules.

## Run and test locally

From the repository root:

```sh
python -m minisvc.cli
# or, after installing the project:
minisvc
python -m compileall minisvc
```

The fixture has no test suite. Add focused tests with `pytest` if that is the project test choice; use a temporary SQLite path via `MINISVC_DB`.

## First trace point

Set the first breakpoint in `minisvc.api.handlers.create_order` at `repo.save(order)`. Trace backward to `register_routes` and forward into `OrderRepository.save`; inspect the payload, generated `Order`, database path, and SQLite exception behavior. For startup issues, begin at `minisvc.cli.main` line 8.

## Two safe first changes

1. Add characterization tests for CLI schema setup, create/read behavior, malformed payload exceptions, and the fact that audit events are currently response-only. Tests do not alter runtime behavior.
2. Add narrow input validation and stable error mapping in `api.handlers`, behind tests, without changing storage or readonly semantics until those contracts are agreed.

## Current behavior to keep in mind

`MINISVC_READONLY` is parsed but not enforced. SQLite writes have no retry loop. Audit events are not durable. The relative default `orders.sqlite` depends on the working directory. These are deliberate review points, not features to assume from the older README notes.

# New engineer onboarding plan

## Recommended read order

1. Read `README.md`, especially its statement that executable code is authoritative over the older design notes.
2. Read `pyproject.toml` to find the console entry point: `minisvc -> minisvc.cli:main`.
3. Read `minisvc/cli.py` and `minisvc/config.py` to understand startup and environment configuration.
4. Read `minisvc/models.py`, then `minisvc/storage/repo.py` for the `Order` shape and SQLite schema/queries.
5. Read `minisvc/api/routes.py` and `minisvc/api/handlers.py` for HTTP registration and request flow.
6. Read `minisvc/audit.py` to verify that events are formatted in memory, not persisted.
7. Treat `minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` as package markers, not active business logic.

## Local run and test commands

From the repository root:

```sh
python -m minisvc.cli
MINISVC_DB=/tmp/minisvc-orders.sqlite python -m minisvc.cli
python -m compileall minisvc
python -m pytest
```

There is no test suite or pytest dependency in the fixture, so the last command may report that no tests are collected or that pytest is unavailable. The CLI command only initializes the database and exits; it does not launch an HTTP server. To exercise the HTTP flow, use a small injected app object implementing `post` and `get`, call `register_routes(app, OrderRepository(path))`, then invoke the captured POST handler.

## First debugging trace point

Start at `minisvc.api.handlers.create_order()` line 6. Set a breakpoint or log the incoming `payload`, then step through `Order(...)`, `OrderRepository.save()` in `minisvc/storage/repo.py`, and `order_event()`. This reveals validation gaps, database errors, and the fact that the event is response-only. For startup issues, the first trace point is `minisvc.cli.main()` line 8, immediately before `load_settings(os.environ)`.

## Two safe first changes

1. Add focused tests (without changing runtime behavior) for `load_settings()` defaults/environment overrides, `create_order()` happy path, `get_order()` missing path, and `OrderRepository` round-trip persistence. Keep package marker files untouched.
2. Improve observability only: add structured/logging diagnostics around `main()`, `init_schema()`, and handler entry/exit/error paths, taking care not to log customer data or secrets. This is safer than immediately changing readonly, retry, or audit semantics.

Before changing behavior, write regression tests for the desired policy. In particular, readonly enforcement, SQLite retry semantics, durable audit storage, and API error responses are currently documented aspirations rather than implemented behavior.

# minisvc architecture

## Overview

`minisvc` is a small order service with two integration surfaces: a console-script bootstrap and an HTTP adapter. The implementation is intentionally small. The README says the code is authoritative when design notes disagree with it.

## Modules

- `minisvc.cli` — active CLI startup code. `main()` loads configuration, creates the repository, initializes the schema, prints readiness, and exits. It does not create or run an HTTP server.
- `minisvc.config` — active configuration code. `load_settings()` reads `MINISVC_DB` and `MINISVC_READONLY` into the frozen `Settings` dataclass.
- `minisvc.models` — active domain model containing the mutable `Order` dataclass.
- `minisvc.storage.repo` — active SQLite persistence. `OrderRepository` owns schema initialization, inserts, and lookups.
- `minisvc.api.routes` — active route adapter. `register_routes(app, repo)` binds `POST /orders` and `GET /orders/<order_id>`.
- `minisvc.api.handlers` — active request handling. It constructs `Order`, calls repository methods, and returns plain dictionaries.
- `minisvc.audit` — active event formatting, but not an audit store. `order_event()` only returns a dictionary.
- `minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are package marker files (the top-level file has a small `__all__` declaration). They are not business-logic modules.

## Entry points

The `pyproject.toml` console script maps `minisvc` to `minisvc.cli:main`. The API integration entry point is `minisvc.api.routes:register_routes`. The handlers exposed through the routes are `minisvc.api.handlers:create_order` and `minisvc.api.handlers:get_order`.

## Data flow

At startup, `main()` passes the process environment to `load_settings()`. The resulting database path is passed to `OrderRepository`, whose `init_schema()` creates `orders(order_id primary key, customer not null, total_cents not null)`.

For a create request, route registration supplies the request payload and shared repository to `create_order()`. The handler indexes required payload keys, converts `total_cents` with `int()`, constructs an `Order`, and calls `repo.save()`. The response includes a formatted `order_event(order, "created")`. For a read request, `get_order()` calls `repo.get()` and returns either a `missing` response or the reconstructed order plus a `read` event.

## Storage and audit behavior

SQLite is the only storage backend, selected by `MINISVC_DB` and defaulting to `orders.sqlite`. Each repository operation opens its own connection with `sqlite3.connect`; writes use parameterized SQL. There is no explicit transaction/retry layer beyond SQLite's context manager behavior.

Despite the README's older design note, no audit table exists and `minisvc.audit.order_event()` does not persist anything. Events exist only in returned response dictionaries. Also, `Settings.readonly` is loaded but never consulted by CLI, routes, handlers, or repository, so `MINISVC_READONLY=1` does not block writes. `create_order()` has no retry loop; SQLite failures propagate.

## Important runtime flow

CLI: console script -> `minisvc.cli:main` -> `load_settings(os.environ)` -> `OrderRepository(...)` -> `init_schema()` -> readiness print -> return 0.

HTTP create: `register_routes(app, repo)` -> POST `/orders` lambda -> `create_order(payload, repo)` -> `Order(...)` and `int(total_cents)` -> `repo.save(order)` -> `order_event(..., "created")` -> response. No HTTP server lifecycle is implemented in this repository.

## Risks and extension points

- Durability and concurrency: SQLite connections are short-lived and errors are not retried or translated. Add an explicit repository policy for busy/locked errors, transaction boundaries, and deployment/database backup strategy.
- Audit requirements: replace or extend `order_event()` with an injected audit sink and an actual schema/table if durable, atomic audit records are required.
- Readonly mode: enforce `Settings.readonly` at the handler or repository boundary, preferably with tests proving every write path is blocked.
- Input validation: missing keys raise `KeyError`, invalid totals raise `ValueError`, and there are no checks for empty/negative values, payload shape, or maximum sizes. Add a validated request model and deliberate error mapping.
- API adapter: route lambdas assume an `app` object with `post` and `get`; there is no framework dependency, server startup, or response/error middleware. An integration layer can provide those concerns.
- Duplicate order IDs raise the underlying SQLite integrity error; decide whether the API should return a conflict response.

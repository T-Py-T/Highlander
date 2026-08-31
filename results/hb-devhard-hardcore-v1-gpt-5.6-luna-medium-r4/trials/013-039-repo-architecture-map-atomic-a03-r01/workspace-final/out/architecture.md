# minisvc architecture

## Modules

The active runtime is small and layered:

- `minisvc.cli:main` is the console bootstrap declared in `pyproject.toml`. It loads config, builds `OrderRepository`, creates the schema, and prints readiness.
- `minisvc.config` maps `MINISVC_DB` and `MINISVC_READONLY` into frozen `Settings`.
- `minisvc.models.Order` is the sole domain model.
- `minisvc.api.routes:register_routes` binds `POST /orders` and `GET /orders/<order_id>` to handlers.
- `minisvc.api.handlers` validates only by direct field access and integer conversion, then calls the repository and event builder.
- `minisvc.storage.repo.OrderRepository` owns SQLite schema, insert, and lookup operations.
- `minisvc.audit:order_event` builds response data in memory.

`minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are package marker files, not business-logic modules.

## Entry points and data flow

The executable entry point is `minisvc.cli:main`; the API integration point is `minisvc.api.routes:register_routes`. On create, the adapter passes a payload to `create_order`, which constructs an `Order`, writes it through `OrderRepository.save`, and returns a dict with an event. Reads call `OrderRepository.get`, reconstruct an `Order`, and return its `__dict__` plus a read event.

## Storage

SQLite is selected by `MINISVC_DB`, defaulting to `orders.sqlite`. `init_schema` creates an `orders` table with a primary key and non-null customer and total. `save` uses parameterized SQL and a connection context manager; `get` opens a fresh connection per query. There is no audit table: `order_event` only returns a dict, and the event is not passed to storage.

## Risks and extension points

- `Settings.readonly` is never checked by CLI, routes, handlers, or repository, so writes still happen when `MINISVC_READONLY=1`.
- There is no retry loop around SQLite writes, and duplicate IDs or database errors propagate.
- Required payload fields are accessed directly; missing fields, invalid totals, oversized values, and unknown fields have no explicit policy.
- The database path is environment-controlled and parent-directory creation, migrations, locking, and backup are unspecified.
- Audit output is ephemeral and returned only in API responses; it is not durable or transactional with order writes.

Natural extension points are a repository policy layer for readonly/retry behavior, explicit request validation at the handler boundary, and a durable audit repository with a transaction strategy.

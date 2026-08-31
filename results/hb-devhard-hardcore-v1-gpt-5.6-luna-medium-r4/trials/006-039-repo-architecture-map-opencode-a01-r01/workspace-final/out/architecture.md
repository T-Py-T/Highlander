# minisvc Architecture

## Purpose

`minisvc` is a small order service with a console bootstrap and a framework-neutral HTTP adapter. The fixture code is authoritative over the older README notes.

## Modules

- `minisvc.cli`: console startup. It loads settings, initializes SQLite schema, prints readiness, and exits; it does not launch an HTTP server.
- `minisvc.config`: `Settings` and `load_settings`, which read `MINISVC_DB` and `MINISVC_READONLY`.
- `minisvc.models`: the `Order` dataclass (`order_id`, `customer`, `total_cents`).
- `minisvc.storage.repo`: `OrderRepository`, the SQLite schema, insert, and lookup implementation.
- `minisvc.audit`: `order_event`, a pure event-dictionary factory.
- `minisvc.api.routes`: registers `POST /orders` and `GET /orders/<order_id>`.
- `minisvc.api.handlers`: converts payloads to orders, invokes the repository, and builds responses.

The `__init__.py` files are package markers (the root one only sets `__all__`); they are not business-logic modules.

## Entry Points

- Console script `minisvc`, configured as `minisvc.cli:main` in `pyproject.toml`.
- API setup function `minisvc.api.routes:register_routes`.
- Registered handlers `minisvc.api.handlers:create_order` and `minisvc.api.handlers:get_order`.

## Data Flow

At startup, `main` reads process environment settings, constructs `OrderRepository`, and calls `init_schema`. An HTTP host must create or supply an `app` and repository, then call `register_routes`.

For `POST /orders`, the route passes a payload to `create_order`. Required keys are read directly; `total_cents` is converted with `int()`. The resulting `Order` is inserted, then `order_event` creates a response-only created event. `GET /orders/<order_id>` reads from SQLite and returns either `missing` or order fields plus a response-only read event.

## Storage

SQLite is opened per repository operation using `database_path`, defaulting to `orders.sqlite` in the current working directory. The only schema is `orders(order_id primary key, customer not null, total_cents integer not null)`. There is no audit table, migration layer, transaction abstraction, or explicit durability policy beyond SQLite context-manager commits.

## Risks and Extension Points

- `MINISVC_READONLY` is parsed but never consulted by CLI, routes, handlers, or repository writes. Enforce it at a shared repository/service boundary before exposing the setting as a guarantee.
- `create_order` has no retry handling; save failures propagate to the caller.
- Audit events are returned in API responses but are not persisted, so they cannot support durable history or reliable compliance replay.
- Direct payload indexing and `int()` conversion allow `KeyError`/`ValueError` to escape. Add explicit request validation and an error mapping layer.
- The CLI has no HTTP server construction, and the adapter assumes an `app` object with `post` and `get` methods. Integrating a real framework is the natural runtime extension point.
- The default relative database path and per-operation connections make deployment working-directory and concurrency choices important.

# minisvc architecture summary

## Overview

`minisvc` is a small order service with two boundaries: a console-script bootstrap and an HTTP adapter. The implementation is intentionally thin: route handlers directly receive an injected `OrderRepository`, and the repository opens a fresh SQLite connection for each operation.

## Active modules

- `minisvc.cli` (`minisvc/cli.py`): `main` loads environment settings, constructs the repository, initializes the schema, and prints readiness. The package script in `pyproject.toml` maps `minisvc` to `minisvc.cli:main`.
- `minisvc.config` (`minisvc/config.py`): `Settings` and `load_settings`. `MINISVC_DB` selects the database path; `MINISVC_READONLY=1` is parsed into `Settings.readonly`.
- `minisvc.models` (`minisvc/models.py`): the `Order` dataclass (`order_id`, `customer`, `total_cents`).
- `minisvc.storage.repo` (`minisvc/storage/repo.py`): `OrderRepository.init_schema`, `save`, and `get` over the SQLite `orders` table.
- `minisvc.api.routes` (`minisvc/api/routes.py`): `register_routes(app, repo)` binds `POST /orders` and `GET /orders/<order_id>`.
- `minisvc.api.handlers` (`minisvc/api/handlers.py`): `create_order` and `get_order`; these perform payload conversion, repository calls, and response shaping.
- `minisvc.audit` (`minisvc/audit.py`): `order_event` creates an event dictionary for responses.

The empty `minisvc/api/__init__.py` and `minisvc/storage/__init__.py`, plus the small `minisvc/__init__.py` `__all__` declaration, are package marker/namespace files rather than business-logic modules. They should not be used as the starting point for understanding runtime behavior.

## Entry points

- CLI: `minisvc.cli:main`, exposed as the `minisvc` project script.
- API setup: `minisvc.api.routes:register_routes`.
- HTTP handlers: `minisvc.api.handlers:create_order` for `POST /orders`, and `minisvc.api.handlers:get_order` for `GET /orders/<order_id>`.

## Data flow

### CLI startup

`main` -> `load_settings(os.environ)` -> `OrderRepository(settings.database_path)` -> `repo.init_schema()` -> readiness print. Although settings includes `readonly`, `main` does not pass it into the repository and `init_schema` always performs a write-capable schema operation.

### HTTP create-order

The host application injects `app` and `repo` into `register_routes`. A POST payload reaches `create_order`, which indexes three required keys and applies `int()` to `total_cents`. It creates an `Order`, calls `repo.save(order)`, then calls `order_event(order, "created")` and returns the response. Exceptions from missing keys, integer conversion, or SQLite are not translated in this layer.

The read path is similar: `get_order` calls `repo.get`, returns `status=missing` when no row exists, or serializes `order.__dict__` and includes a generated read event.

## Storage and audit behavior

SQLite is the only persistence mechanism. `OrderRepository` stores the path as a `Path` and uses `sqlite3.connect` in `with` blocks, so each operation commits or rolls back through the connection context manager. The schema contains only `orders(order_id primary key, customer not null, total_cents not null)`. There is no migration/version table, connection pooling, explicit WAL/backup policy, or audit table.

Audit is response construction only. `minisvc.audit:order_event` returns a plain dictionary; neither `create_order` nor `get_order` persists that dictionary. The created/read event therefore disappears after the response unless the host application stores it elsewhere.

## Risks and extension points

- **Readonly is not enforced:** `load_settings` parses the flag, but `OrderRepository` has no readonly field and handlers still call `save`. Add an explicit policy boundary and test every write path, including schema initialization.
- **No retry behavior:** `create_order` calls `repo.save` once. Transient SQLite failures propagate. If retries are added, bound them, classify retryable errors, and consider idempotency for duplicate order IDs.
- **Durability and concurrency:** per-call SQLite connections and a path defaulting to a relative `orders.sqlite` make runtime location/environment important. Define deployment storage, backups, locking/WAL policy, and migrations before scaling.
- **Input validation:** required-key indexing and `int()` are the only validation. Negative totals, empty IDs/customers, oversized values, and booleans or malformed numeric strings are not governed by an explicit contract. Add schema validation and consistent client error responses.
- **Audit extension:** replace or wrap `order_event` with a durable audit repository if auditability is required; define transaction ordering so an order cannot be committed without its audit record (or vice versa).

The injected `app` and repository in `register_routes` are useful extension points: a real web adapter can supply framework request/response conversion, while tests can inject a fake repository.

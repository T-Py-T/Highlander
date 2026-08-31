# minisvc Architecture

## Overview

`minisvc` is a small Python service with two visible entry surfaces:

- `minisvc.cli:main` bootstraps the runtime, loads environment settings, opens the SQLite repository, and creates the schema.
- `minisvc.api.routes:register_routes` wires HTTP routes to the order handlers.

The active runtime code is concentrated in:

- `minisvc/cli.py`
- `minisvc/config.py`
- `minisvc/api/routes.py`
- `minisvc/api/handlers.py`
- `minisvc/storage/repo.py`
- `minisvc/models.py`
- `minisvc/audit.py`

The package marker files `minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` do not contain business logic.

## Modules

- `minisvc.config` defines `Settings` and `load_settings(env)`. It resolves `MINISVC_DB` into the SQLite file path and parses `MINISVC_READONLY`, although the readonly flag is not consumed elsewhere.
- `minisvc.cli` is the CLI startup path. It loads settings, instantiates `OrderRepository`, calls `init_schema()`, and prints the database path.
- `minisvc.models` contains the `Order` dataclass shared by handlers, audit, and storage.
- `minisvc.api.routes` exposes `register_routes(app, repo)`, binding `POST /orders` and `GET /orders/<order_id>` to handler lambdas.
- `minisvc.api.handlers` contains the request logic:
  - `create_order(payload, repo)` builds an `Order`, writes it, and returns a response with an event dict.
  - `get_order(order_id, repo)` fetches the row and returns either `missing` or the order payload plus an event dict.
- `minisvc.audit` provides `order_event(order, action)`, which only builds an in-memory dictionary.
- `minisvc.storage.repo` is the persistence layer. `OrderRepository` creates the `orders` table, inserts rows, and fetches rows from SQLite.

## Entry Points

- CLI: `minisvc.cli:main`
- Route registration: `minisvc.api.routes:register_routes`
- Request handlers used by the route layer:
  - `minisvc.api.handlers:create_order`
  - `minisvc.api.handlers:get_order`

## Data Flow

### CLI startup

1. `minisvc.cli:main` reads environment variables through `load_settings(os.environ)`.
2. It constructs `OrderRepository(settings.database_path)`.
3. It initializes the schema with `repo.init_schema()`.
4. It reports readiness via stdout.

### HTTP create-order flow

1. An outer app setup passes `app` and `repo` into `register_routes`.
2. `POST /orders` invokes `create_order(payload, repo)`.
3. `create_order` extracts `order_id`, `customer`, and `total_cents` from the payload.
4. The handler constructs `Order(...)` and calls `repo.save(order)`.
5. `repo.save` inserts into the SQLite `orders` table.
6. The handler creates an event dict with `order_event(order, "created")`.
7. The response returns the created status, order ID, and event payload.

### HTTP read flow

1. `GET /orders/<order_id>` invokes `get_order(order_id, repo)`.
2. `repo.get(order_id)` queries SQLite.
3. If no row exists, the handler returns `{"status": "missing"}`.
4. Otherwise it returns the order fields and a `read` event dict.

## Storage

- Persistent storage is a single SQLite database file.
- The only schema created in code is `orders(order_id text primary key, customer text not null, total_cents integer not null)`.
- Each repository operation opens a fresh SQLite connection with `sqlite3.connect(self.database_path)`.
- Audit data is not stored in SQLite, a file, or any external system. It is only generated as a response field.

## Risks And Extension Points

### Main risks

- Readonly mode is configured but not enforced. `MINISVC_READONLY=1` sets `Settings.readonly`, but neither the CLI nor the handlers use it to block writes.
- Write failures are not retried. `create_order` directly calls `repo.save(order)`, and `save` does not wrap SQLite errors.
- Audit behavior is non-durable. The code never creates or writes an audit table despite the design note in `README.md`.
- API input validation is minimal. Missing keys, non-integer `total_cents`, and duplicate `order_id` values can raise uncaught exceptions.
- Startup only prepares the `orders` table. Any future expansion of persistence will need explicit migration handling.

### Natural extension points

- Enforce readonly mode in `create_order` or inside `OrderRepository.save`.
- Replace lambda route wrappers in `register_routes` if request context or structured error mapping becomes necessary.
- Move response shaping and validation into a dedicated service layer if the API grows beyond two handlers.
- Expand `OrderRepository` with explicit transaction, retry, and migration policies once concurrency or durability requirements increase.
- Turn `order_event` into a persistence-backed audit subsystem if event history becomes part of the contract.

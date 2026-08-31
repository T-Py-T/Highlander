# minisvc architecture summary

## What this repo is
`minisvc` is a small Python service skeleton with two live runtime surfaces:
- a CLI bootstrap command at `minisvc.cli:main`
- HTTP route registration at `minisvc.api.routes:register_routes`

It stores orders in SQLite through one repository class. The repo has no built-in web server module; an outside app object must call `register_routes(app, repo)`.

Do not treat these files as business logic:
- `minisvc/__init__.py`
- `minisvc/api/__init__.py`
- `minisvc/storage/__init__.py`

They are package markers or export stubs only.

## Main modules
- `minisvc/config.py` — loads `MINISVC_DB` and `MINISVC_READONLY` into `Settings`
- `minisvc/models.py` — defines the `Order` dataclass
- `minisvc/storage/repo.py` — owns SQLite schema setup, inserts, and reads
- `minisvc/audit.py` — formats audit event dicts; it does not save them
- `minisvc/api/handlers.py` — core create/get order logic
- `minisvc/api/routes.py` — wires handlers into an external HTTP adapter
- `minisvc/cli.py` — startup path for local bootstrap

## Entry points
- `minisvc.cli:main` — exposed as the `minisvc` console script in `pyproject.toml`
- `minisvc.api.routes:register_routes` — API setup entry point for an external app
- Handler entry points used by the HTTP adapter:
  - `minisvc.api.handlers:create_order`
  - `minisvc.api.handlers:get_order`

## Data flow
### CLI startup flow
1. `minisvc.cli:main` reads env through `load_settings(os.environ)`.
2. It builds `OrderRepository(settings.database_path)`.
3. It calls `repo.init_schema()`.
4. The repository creates the `orders` table if needed.
5. The CLI prints the ready path and exits.

### HTTP create-order flow
1. An outside app calls `register_routes(app, repo)`.
2. `register_routes` binds POST `/orders` to `create_order(payload, repo)`.
3. `create_order` builds an `Order` from `payload["order_id"]`, `payload["customer"]`, and `int(payload["total_cents"])`.
4. It calls `repo.save(order)`.
5. `OrderRepository.save` opens SQLite and inserts one row into `orders`.
6. The handler returns a response dict with status, order id, and an inline event from `order_event(order, "created")`.

### HTTP get-order flow
1. GET `/orders/<order_id>` calls `get_order(order_id, repo)`.
2. The handler calls `repo.get(order_id)`.
3. The repository reads from SQLite and returns `Order` or `None`.
4. The handler returns either `{"status": "missing"}` or `{"status": "ok", "order": ..., "event": ...}`.

## Storage
- Storage backend: SQLite via `sqlite3` in `minisvc/storage/repo.py`
- File path source: `MINISVC_DB`, default `orders.sqlite`
- Schema: one table, `orders(order_id text primary key, customer text not null, total_cents integer not null)`
- Audit storage: none in code. Audit data is only a returned dict from `minisvc.audit.order_event`

## Config and runtime behavior
- `MINISVC_DB` sets the SQLite file path
- `MINISVC_READONLY` is parsed into `Settings.readonly`
- No live code uses `Settings.readonly` after config load
- No retry loop wraps `repo.save`
- No app factory, dependency injection container, or transaction wrapper exists beyond per-call SQLite context managers

## Risks and extension points
### Risks
- Readonly mode is documented but not enforced. Write paths still call `repo.save`.
- Create-order has no payload validation beyond direct key access and `int(...)` casting. Bad input raises exceptions.
- Audit events are not durable. They are response data only.
- Each repository method opens its own SQLite connection. There is no retry, no busy timeout setup, and no explicit concurrency strategy.
- The default DB path is relative (`orders.sqlite`), so runtime location depends on the current working directory.

### Good extension points
- `minisvc.api.handlers.create_order` is the place to add input checks, readonly gating, and richer error mapping.
- `minisvc.storage.repo.OrderRepository` is the place to add audit tables, retries, transaction policy, and migrations.
- `minisvc.api.routes.register_routes` is the place to swap lambdas for named adapter functions if the HTTP layer grows.
- `minisvc.config.load_settings` is the place to add new env-driven settings.

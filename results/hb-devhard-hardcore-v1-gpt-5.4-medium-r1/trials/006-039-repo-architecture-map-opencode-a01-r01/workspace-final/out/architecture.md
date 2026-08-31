# minisvc Architecture Summary

## What This Service Actually Contains

`minisvc` is a very small Python service skeleton with two real runtime surfaces:

- A CLI bootstrap entry point at `minisvc.cli:main`
- An HTTP route registration hook at `minisvc.api.routes:register_routes`

It persists orders to a local SQLite database through `OrderRepository`. The package marker files `minisvc/api/__init__.py` and `minisvc/storage/__init__.py` do not contain business logic, and `minisvc/__init__.py` only exports names.

## Runtime Modules

- `minisvc/cli.py`: startup path for the packaged `minisvc` command. Loads config, opens the repository, creates schema, prints readiness.
- `minisvc/config.py`: defines `Settings` and `load_settings(env)`, reading `MINISVC_DB` and `MINISVC_READONLY`.
- `minisvc/models.py`: defines the `Order` dataclass.
- `minisvc/audit.py`: builds an event dictionary for API responses. It does not write any audit records.
- `minisvc/api/routes.py`: attaches HTTP handlers to an external app object via `app.post(...)` and `app.get(...)`.
- `minisvc/api/handlers.py`: implements create and read order actions.
- `minisvc/storage/repo.py`: owns SQLite schema creation and CRUD-like persistence for orders.

## Entry Points

- `minisvc.cli:main`: declared in `pyproject.toml` as the `minisvc` console script.
- `minisvc.api.routes:register_routes`: integration point for wiring HTTP routes into a framework-specific app.
- `minisvc.api.handlers:create_order`: POST `/orders` behavior after route registration.
- `minisvc.api.handlers:get_order`: GET `/orders/<order_id>` behavior after route registration.

## Data Flow

### CLI startup

1. `minisvc.cli:main` reads process environment.
2. `minisvc.config:load_settings` builds a `Settings` object.
3. `main` creates `OrderRepository(settings.database_path)`.
4. `OrderRepository.init_schema()` creates the `orders` table if it is missing.
5. The CLI prints `minisvc ready at ...` and exits.

### HTTP create-order flow

1. Some external application constructs a repository and calls `minisvc.api.routes:register_routes(app, repo)`.
2. The registered POST callback invokes `minisvc.api.handlers:create_order(payload, repo)`.
3. `create_order` extracts `order_id`, `customer`, and `total_cents` from the payload and builds an `Order` dataclass.
4. `repo.save(order)` inserts the order into SQLite.
5. `order_event(order, "created")` generates a response event object.
6. The handler returns a dictionary response.

### HTTP read flow

1. The registered GET callback invokes `minisvc.api.handlers:get_order(order_id, repo)`.
2. `repo.get(order_id)` reads a row from SQLite.
3. The handler returns either `{"status": "missing"}` or `{"status": "ok", "order": ..., "event": ...}`.

## Storage

- Storage engine: SQLite via Python `sqlite3`
- Path source: `MINISVC_DB`, defaulting to `orders.sqlite`
- Schema ownership: `OrderRepository.init_schema()`
- Tables actually created: only `orders`
- Audit persistence: none

Each repository method opens a fresh SQLite connection with `sqlite3.connect(self.database_path)`. There is no connection pooling, no retry wrapper, and no migration/versioning layer.

## Documentation vs Code Reality

The README explicitly says the code is authoritative when docs disagree. In practice, the implementation is simpler than the design notes:

- `MINISVC_READONLY=1` is parsed into `Settings.readonly`, but no write path checks it.
- `create_order` does not retry failed SQLite writes.
- Audit events are returned in response payloads only; there is no durable audit table.

## Risks And Extension Points

### Risks

- Error handling is minimal. Missing payload keys, bad integer conversion, duplicate primary keys, or SQLite failures will raise exceptions directly from handlers.
- Configuration is only partly wired. `readonly` is loaded but ignored by the repository and handlers.
- Audit behavior is non-durable despite documentation claiming durable storage.
- The HTTP layer assumes an app object with `.post` and `.get`, but the repository contains no app factory or server bootstrap, so runtime integration is external and implicit.

### Extension points

- Enforce readonly mode in `minisvc.api.handlers:create_order` or inside `OrderRepository.save`.
- Add explicit request validation and translate failures into stable API responses.
- Introduce durable audit persistence in `minisvc/storage/repo.py` or a separate audit repository.
- Add an application bootstrap module that constructs the app and calls `register_routes` to make the HTTP runtime self-contained.

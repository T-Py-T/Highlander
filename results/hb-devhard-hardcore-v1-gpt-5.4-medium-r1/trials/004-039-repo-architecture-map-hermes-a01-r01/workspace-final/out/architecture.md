# minisvc architecture summary

## What this service does
`minisvc` is a very small order service with two exposed integration surfaces:
- a CLI bootstrap command at `minisvc.cli:main`
- HTTP route registration at `minisvc.api.routes:register_routes`

The business path is narrow: HTTP or other callers hand a payload to order handlers, handlers build an `Order`, and `OrderRepository` persists or reads that order from SQLite.

## Active runtime modules
These files contain the real runtime behavior:
- `minisvc/cli.py`: startup/bootstrap path; loads settings, creates the repository, initializes schema.
- `minisvc/config.py`: environment-to-settings mapping.
- `minisvc/models.py`: `Order` dataclass.
- `minisvc/storage/repo.py`: SQLite storage adapter.
- `minisvc/api/routes.py`: binds route callbacks to an app object.
- `minisvc/api/handlers.py`: create/get order use cases.
- `minisvc/audit.py`: constructs event dictionaries included in responses.

Package marker or dead-simple files that should not be mistaken for business logic:
- `minisvc/__init__.py`: only exports `config` and `models`.
- `minisvc/api/__init__.py`: empty package marker.
- `minisvc/storage/__init__.py`: empty package marker.

## Entry points
- CLI: `minisvc.cli:main` (declared in `pyproject.toml` under `[project.scripts]`)
- HTTP route registration: `minisvc.api.routes:register_routes`
- Route-level handlers: `minisvc.api.handlers:create_order` and `minisvc.api.handlers:get_order`

## Module relationships
1. `minisvc.cli.main` loads `Settings` from environment variables.
2. `main` constructs `OrderRepository(settings.database_path)`.
3. `main` calls `repo.init_schema()` so the `orders` table exists.
4. A host application can pass an app object and repository into `register_routes`.
5. `register_routes` attaches:
   - `POST /orders` -> `create_order(payload, repo)`
   - `GET /orders/<order_id>` -> `get_order(order_id, repo)`
6. The handlers use `OrderRepository` for persistence and `order_event()` for response metadata.

## Data flow
### CLI startup flow
1. Console script resolves to `minisvc.cli:main`.
2. `load_settings(os.environ)` reads `MINISVC_DB` and `MINISVC_READONLY`.
3. `OrderRepository` is created with the configured SQLite file path.
4. `init_schema()` creates the `orders` table if needed.
5. The CLI prints `minisvc ready at ...` and exits.

Important nuance: this is the only schema initialization path present in the repo. If an HTTP host uses `register_routes` without first calling `init_schema()`, writes can fail because the table may not exist.

### HTTP create-order flow
1. A hosting layer invokes `register_routes(app, repo)`.
2. The POST `/orders` route lambda forwards the request payload to `create_order(payload, repo)`.
3. `create_order` directly indexes `payload["order_id"]`, `payload["customer"]`, and `payload["total_cents"]`.
4. `total_cents` is converted with `int(...)` and wrapped in an `Order` dataclass.
5. `repo.save(order)` inserts a row into SQLite.
6. `order_event(order, "created")` generates a dict that is embedded in the response.
7. The response shape is `{"status": "created", "order_id": ..., "event": ...}`.

Observed runtime behavior from local execution: duplicate inserts raise `sqlite3.IntegrityError`, missing fields raise `KeyError`, and non-integer totals raise `ValueError`; these are not handled inside the handler.

### HTTP read-order flow
1. GET `/orders/<order_id>` forwards to `get_order(order_id, repo)`.
2. `repo.get(order_id)` runs a `SELECT`.
3. If no row is found, the handler returns `{"status": "missing", "order_id": ...}`.
4. Otherwise it returns `{"status": "ok", "order": order.__dict__, "event": ...}`.

## Storage
- Primary storage is SQLite in `minisvc/storage/repo.py`.
- Default path is a relative file, `orders.sqlite`, unless `MINISVC_DB` overrides it.
- Only one table is created: `orders(order_id text primary key, customer text not null, total_cents integer not null)`.
- The repository opens a fresh SQLite connection per method call.
- There is no separate audit table, no migration system, and no retry wrapper around writes.

## Configuration and runtime environment
- `MINISVC_DB`: database file path, default `orders.sqlite`
- `MINISVC_READONLY`: parsed into `Settings.readonly`, default false

Important discrepancy: `readonly` is parsed but never enforced by the CLI, routes, handlers, or repository. It is currently configuration state with no downstream behavior.

## Risks and extension points
### Risks
- Read-only mode is documented but not implemented, so operators may assume writes are blocked when they are not.
- Error handling is thin: invalid payloads and SQLite errors propagate directly.
- Audit behavior is response-only; no durable audit record exists.
- Schema setup lives only in the CLI path, so API-only deployments can start without initializing storage.
- Using a relative default database path can create environment-dependent storage locations.

### Good extension points
- Add write-policy enforcement in `minisvc.api.handlers.create_order` or `OrderRepository.save` using `Settings.readonly`.
- Add input validation around `create_order` before building `Order`.
- Introduce persistent audit storage beside `orders` in `OrderRepository`.
- Add a real application bootstrap that combines route registration, config loading, and schema initialization for HTTP deployments.
- Wrap storage calls in error translation so handlers return controlled error responses instead of raw exceptions.

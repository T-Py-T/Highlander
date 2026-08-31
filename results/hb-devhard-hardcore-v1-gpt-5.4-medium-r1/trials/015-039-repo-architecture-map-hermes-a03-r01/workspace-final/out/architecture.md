# minisvc architecture summary

## What this service is
`minisvc` is a very small order service with two integration surfaces:
- a CLI bootstrap command that initializes storage
- an HTTP-style route registration function that wires create/read order handlers onto a host app

The implementation is intentionally small. The real runtime logic lives in `minisvc/cli.py`, `minisvc/config.py`, `minisvc/models.py`, `minisvc/audit.py`, `minisvc/storage/repo.py`, `minisvc/api/handlers.py`, and `minisvc/api/routes.py`.

Do not mistake package marker files for business logic:
- `minisvc/__init__.py` only sets `__all__`
- `minisvc/api/__init__.py` is empty
- `minisvc/storage/__init__.py` is empty

## Module map
- `minisvc.cli`: CLI bootstrap. Loads config, constructs `OrderRepository`, initializes schema, prints readiness.
- `minisvc.config`: `Settings` dataclass plus `load_settings(env)` for `MINISVC_DB` and `MINISVC_READONLY`.
- `minisvc.models`: `Order` dataclass shared across layers.
- `minisvc.audit`: `order_event(order, action)` returns an audit-shaped dict.
- `minisvc.storage.repo`: SQLite persistence layer with `init_schema`, `save`, and `get`.
- `minisvc.api.handlers`: request logic for `create_order` and `get_order`.
- `minisvc.api.routes`: route wiring through `register_routes(app, repo)`.

## Entry points
- `minisvc.cli:main`
  - Exposed as the `minisvc` script in `pyproject.toml`.
  - This is the only concrete executable entry point in the repository.
- `minisvc.api.routes:register_routes`
  - API integration entry point.
  - A host framework or test harness must provide an `app` object with `post()` and `get()` methods.

## Runtime flow
### CLI startup flow
1. `minisvc.cli:main` calls `load_settings(os.environ)`.
2. Config resolves `MINISVC_DB` (default `orders.sqlite`) and `MINISVC_READONLY`.
3. `main` instantiates `OrderRepository(settings.database_path)`.
4. `main` calls `repo.init_schema()`.
5. `init_schema()` opens SQLite and creates the `orders` table if needed.
6. `main` prints `minisvc ready at ...` and returns `0`.

Important nuance: the CLI never enforces the `readonly` setting even though config parses it.

### HTTP create-order flow
1. A host app calls `register_routes(app, repo)`.
2. `register_routes` binds `POST /orders` to a lambda calling `create_order(payload, repo)`.
3. `create_order` reads raw keys from the payload and converts `total_cents` with `int(...)`.
4. `create_order` constructs an `Order` dataclass.
5. `repo.save(order)` inserts into the SQLite `orders` table.
6. `order_event(order, "created")` builds an in-memory event dict.
7. The handler returns `{"status": "created", "order_id": ..., "event": ...}`.

### HTTP read-order flow
1. `register_routes` binds `GET /orders/<order_id>` to `get_order(order_id, repo)`.
2. `get_order` calls `repo.get(order_id)`.
3. Missing rows return `{"status": "missing", "order_id": ...}`.
4. Present rows return `{"status": "ok", "order": order.__dict__, "event": ...}`.

## Data flow
- Inbound config: environment variables into `Settings`.
- Inbound API payload: raw dict into `create_order`.
- Domain object: `Order` dataclass is the shared object passed into repository and audit formatting.
- Persistence: only the `orders` table in SQLite is written.
- Outbound responses: plain Python dicts, not framework response objects.
- Audit data: generated as dicts and embedded in responses; not stored durably.

## Storage
- Backend: SQLite via `sqlite3.connect(...)` per repository method call.
- Schema: a single `orders(order_id text primary key, customer text not null, total_cents integer not null)` table.
- Write path: `OrderRepository.save()` performs one insert.
- Read path: `OrderRepository.get()` fetches one row and rehydrates `Order`.
- Durability caveat: there is no separate audit table, no explicit retry loop, no filesystem path validation, and no application-level transaction/error strategy beyond SQLite context-manager behavior.

## Risks and extension points
### Main risks
- `MINISVC_READONLY` is parsed but never checked on write paths.
- `create_order` trusts payload shape and type coercion; malformed input raises exceptions instead of producing structured validation errors.
- SQLite write failures bubble up directly; there is no retry behavior despite the README claim.
- Audit events are not persisted anywhere durable.
- Route registration assumes a specific `app.post/app.get` API but does not document or type-check that contract.

### Good extension points
- Add readonly enforcement close to `create_order` or `OrderRepository.save`.
- Introduce explicit input validation before building `Order`.
- Add exception translation around SQLite operations for duplicate IDs and database availability issues.
- Replace or extend `order_event` with durable audit persistence if compliance/history matters.
- Add a thin real web framework adapter around `register_routes` if the service needs runnable HTTP hosting inside this repo.

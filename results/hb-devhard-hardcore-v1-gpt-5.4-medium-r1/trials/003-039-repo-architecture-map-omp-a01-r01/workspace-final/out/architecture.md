# minisvc architecture

## What is active runtime code
- Business/runtime modules: `minisvc.cli`, `minisvc.config`, `minisvc.models`, `minisvc.audit`, `minisvc.api.routes`, `minisvc.api.handlers`, `minisvc.storage.repo`.
- Package markers only: `minisvc/__init__.py` and `minisvc/storage/__init__.py` are empty; `minisvc/api/__init__.py` only sets `__all__`. They are not business logic modules.

## Module map
- `minisvc.cli` — console bootstrap. Loads env config, creates `OrderRepository`, initializes schema, prints readiness.
- `minisvc.config` — `Settings` dataclass plus `load_settings(env)`.
- `minisvc.models` — `Order` dataclass.
- `minisvc.audit` — `order_event(order, action)` formatter for response metadata.
- `minisvc.api.routes` — attaches `/orders` routes to an app object.
- `minisvc.api.handlers` — request handlers for create/read order flows.
- `minisvc.storage.repo` — direct SQLite access for schema bootstrap, insert, and lookup.

## Entry points
- CLI: `minisvc.cli:main` via `pyproject.toml` console script `minisvc`.
- HTTP registration: `minisvc.api.routes:register_routes`.
- HTTP handler endpoints behind route registration: `minisvc.api.handlers:create_order`, `minisvc.api.handlers:get_order`.

## Data flow
### CLI startup
1. `minisvc.cli:main` calls `minisvc.config:load_settings(os.environ)`.
2. `load_settings` resolves `MINISVC_DB` and `MINISVC_READONLY`.
3. `main` instantiates `OrderRepository(settings.database_path)`.
4. `main` calls `repo.init_schema()`.
5. SQLite creates `orders(order_id text primary key, customer text not null, total_cents integer not null)` if missing.
6. CLI prints the database path and exits.

### HTTP create-order flow
1. The host app calls `register_routes(app, repo)`.
2. `POST /orders` dispatches to `create_order(payload, repo)`.
3. `create_order` expects `order_id`, `customer`, and `total_cents` keys in the payload.
4. `total_cents` is coerced with `int(...)`; malformed input raises `ValueError`.
5. The handler constructs an `Order` dataclass and calls `repo.save(order)`.
6. `OrderRepository.save` performs one SQLite `insert into orders(...)`.
7. The handler returns a response dict with `status`, `order_id`, and an embedded audit event from `order_event`.

### HTTP read flow
1. `GET /orders/<order_id>` dispatches to `get_order(order_id, repo)`.
2. `repo.get(order_id)` queries SQLite by primary key.
3. Missing rows return `{'status': 'missing', 'order_id': ...}`.
4. Found rows return `{'status': 'ok', 'order': order.__dict__, 'event': ...}`.

## Storage
- Only persistent store: SQLite file at `Settings.database_path`, default `orders.sqlite` in the current working directory.
- Only table created by code: `orders`.
- No audit table, migration layer, pooling, or retry mechanism.
- Each repository method opens a fresh `sqlite3.connect(...)` context.

## Risks and extension points
### Risks
- Readonly mode is configuration-only. `MINISVC_READONLY` is parsed but never checked before writes.
- Input validation is minimal. Missing payload keys raise `KeyError`; bad `total_cents` raises `ValueError`; repository errors bubble unchanged.
- Audit behavior is non-durable. `order_event` returns a dict but does not persist anything.
- Durability/runtime behavior depends on process cwd unless `MINISVC_DB` is set.
- The route layer assumes an `app` object with `.post()` and `.get()`; there is no adapter contract enforcement.

### Extension points
- Add validation and error translation in `minisvc.api.handlers`.
- Enforce readonly policy in `create_order` or in `OrderRepository.save` after threading `Settings` through.
- Replace or wrap `OrderRepository` to add transactions, retries, migrations, or alternate storage.
- Expand `order_event` into a real audit sink if durable audit history is required.

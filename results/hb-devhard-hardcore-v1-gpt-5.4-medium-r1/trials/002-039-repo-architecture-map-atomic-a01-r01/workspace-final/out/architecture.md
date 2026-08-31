# minisvc architecture

## What this repo does
`minisvc` is a small Python service slice with two main faces:
- a CLI bootstrap path that creates the SQLite schema
- HTTP-style route registration and handlers for creating and reading orders

The live runtime code is in these modules:
- `minisvc/cli.py`
- `minisvc/config.py`
- `minisvc/models.py`
- `minisvc/audit.py`
- `minisvc/api/handlers.py`
- `minisvc/api/routes.py`
- `minisvc/storage/repo.py`

Package marker files such as `minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are not business logic modules.

## Modules

### `minisvc/cli.py`
CLI entry point. `main()` loads config from the environment, creates `OrderRepository`, initializes the `orders` table, prints a ready line, and exits.

### `minisvc/config.py`
Defines immutable `Settings` and `load_settings(env)`. It reads:
- `MINISVC_DB` for the SQLite file path
- `MINISVC_READONLY` for a boolean flag

### `minisvc/models.py`
Defines the `Order` dataclass with `order_id`, `customer`, and `total_cents`.

### `minisvc/audit.py`
Defines `order_event(order, action)`. It builds a dict for response metadata. It does not write to storage.

### `minisvc/api/handlers.py`
Holds the request handlers:
- `create_order(payload, repo)` builds an `Order`, saves it, and returns a response dict
- `get_order(order_id, repo)` reads an order and returns either `missing` or `ok`

### `minisvc/api/routes.py`
Defines `register_routes(app, repo)`. It expects an app object with `.post()` and `.get()` methods and wires two routes:
- `POST /orders`
- `GET /orders/<order_id>`

### `minisvc/storage/repo.py`
Defines `OrderRepository`, the SQLite adapter. It:
- stores the database path
- creates the `orders` table
- inserts new rows
- reads rows by `order_id`

## Entry points
- `minisvc.cli:main` — console script entry from `pyproject.toml`
- `minisvc.api.routes:register_routes` — API registration hook for an embedding HTTP app
- `minisvc.api.handlers:create_order` — handler used by `POST /orders`
- `minisvc.api.handlers:get_order` — handler used by `GET /orders/<order_id>`

## Runtime flows

### CLI startup
1. The `minisvc` console script calls `minisvc.cli:main`.
2. `main()` calls `load_settings(os.environ)`.
3. Settings resolve the SQLite path and readonly flag.
4. `main()` creates `OrderRepository(settings.database_path)`.
5. `main()` calls `repo.init_schema()`.
6. The process prints `minisvc ready at ...` and exits.

Important note: schema setup happens here, not in the HTTP handler path.

### HTTP create-order flow
1. The host app calls `register_routes(app, repo)`.
2. `register_routes()` binds `POST /orders` to `create_order(payload, repo)`.
3. `create_order()` pulls raw keys from the payload and casts `total_cents` with `int(...)`.
4. `repo.save(order)` inserts a row into SQLite.
5. `order_event(order, "created")` builds an event dict.
6. The handler returns `{"status": "created", "order_id": ..., "event": ...}`.

### HTTP get-order flow
1. `GET /orders/<order_id>` reaches `get_order(order_id, repo)`.
2. `repo.get(order_id)` queries SQLite.
3. The handler returns either a `missing` response or the order plus a read event dict.

## Data flow
- Input enters through the CLI environment or handler payloads.
- `config.py` turns env vars into `Settings`.
- `handlers.py` turns request data into `Order` objects.
- `storage/repo.py` is the only persistent data layer.
- `audit.py` builds response-side event data, but that data is not durable.

## Storage
- Backend: SQLite via the standard `sqlite3` module
- Database file: path from `MINISVC_DB`, default `orders.sqlite`
- Tables actually created: only `orders`
- Per-call pattern: each repository method opens its own SQLite connection with a context manager

There is no audit table, migration layer, or explicit transaction policy beyond SQLite's default connection context behavior.

## Risks and extension points

### Risks
- **Readonly flag is not enforced.** `load_settings()` reads it, but no write path checks it.
- **No retry behavior on writes.** `create_order()` calls `repo.save()` once.
- **Audit is not durable.** Audit events are returned in responses only.
- **Input validation is thin.** Missing keys raise `KeyError`; bad `total_cents` raises `ValueError`; there is no explicit API error mapping here.
- **Schema init is easy to miss.** The CLI creates the table, but the HTTP path does not.
- **DB path depends on runtime cwd.** The default `orders.sqlite` is relative.

### Extension points
- Enforce readonly in `create_order()` or `OrderRepository.save()`.
- Add request validation before building `Order`.
- Add a durable audit store if audit history matters.
- Add retry or error mapping around SQLite writes if transient failures matter.
- Move schema setup into app startup, not just the CLI bootstrap path.

# minisvc Architecture Summary

## What Runs

`minisvc` is a very small Python service skeleton with two active runtime surfaces:

- `minisvc.cli:main`: CLI bootstrap exposed by `pyproject.toml` as the `minisvc` command.
- `minisvc.api.routes:register_routes`: HTTP adapter hook that wires order routes onto an external app object.

The package marker files `minisvc/api/__init__.py` and `minisvc/storage/__init__.py` do not contain business logic. `minisvc/__init__.py` only exports names.

## Modules

- `minisvc/cli.py`: Loads environment settings, constructs `OrderRepository`, initializes the SQLite schema, and prints readiness.
- `minisvc/config.py`: Defines `Settings` and `load_settings(env)` for `MINISVC_DB` and `MINISVC_READONLY`.
- `minisvc/models.py`: Defines the `Order` dataclass.
- `minisvc/audit.py`: Builds event dictionaries from an `Order` and action string.
- `minisvc/api/routes.py`: Registers `POST /orders` and `GET /orders/<order_id>` against an external app interface.
- `minisvc/api/handlers.py`: Implements create and read order behavior.
- `minisvc/storage/repo.py`: Owns SQLite schema initialization and order persistence.

## Entry Points

- `minisvc.cli:main`: canonical CLI entry point.
- `minisvc.api.routes:register_routes`: canonical HTTP registration hook.
- `minisvc.api.handlers:create_order`: effective request handler for `POST /orders`.
- `minisvc.api.handlers:get_order`: effective request handler for `GET /orders/<order_id>`.

## Data Flow

### CLI Startup

1. Packaging invokes `minisvc.cli:main`.
2. `main` reads environment variables through `os.environ`.
3. `load_settings` maps `MINISVC_DB` to `Settings.database_path` and `MINISVC_READONLY` to `Settings.readonly`.
4. `main` builds `OrderRepository(settings.database_path)`.
5. `main` calls `repo.init_schema()` to create the `orders` table if needed.
6. The CLI prints `minisvc ready at ...` and exits.

### HTTP Create-Order Flow

1. An external application passes `app` and `repo` into `register_routes`.
2. `register_routes` binds `POST /orders` to `create_order(payload, repo)`.
3. `create_order` reads `order_id`, `customer`, and `total_cents` directly from the payload.
4. `create_order` converts `total_cents` with `int(...)` and constructs an `Order`.
5. `repo.save(order)` inserts the row into SQLite.
6. `order_event(order, "created")` creates a response event object.
7. The handler returns `{"status": "created", "order_id": ..., "event": ...}`.

### HTTP Read Flow

1. `register_routes` binds `GET /orders/<order_id>` to `get_order(order_id, repo)`.
2. `get_order` calls `repo.get(order_id)`.
3. If no row exists, the handler returns `{"status": "missing", "order_id": ...}`.
4. Otherwise it returns the order contents and an in-memory `read` event.

## Storage

- Storage is a single SQLite database file accessed through `sqlite3.connect(...)` in `OrderRepository`.
- The only table created is `orders(order_id text primary key, customer text not null, total_cents integer not null)`.
- The default database path is the relative filename `orders.sqlite`.
- There is no audit table, migration layer, retry logic, or explicit connection/session management abstraction.

## Risks And Extension Points

- Readonly mode is configured but not enforced. `MINISVC_READONLY` is parsed in `load_settings`, but no write path checks `Settings.readonly` before calling `repo.save(...)`.
- Schema creation is only guaranteed in the CLI path. The HTTP integration path assumes the caller constructed a repository and initialized the schema elsewhere.
- Input validation is thin. `create_order` depends on required keys existing and on `int(payload["total_cents"])` succeeding.
- Audit output is response-only. `order_event` creates dictionaries, but nothing writes them to durable storage despite the design note.
- Error handling is minimal. SQLite exceptions, duplicate keys, and malformed payloads will bubble directly.

Useful extension points:

- Add service-layer logic between handlers and repository if business rules grow.
- Enforce readonly behavior either in handlers or repository methods.
- Replace route lambdas with explicit adapter functions if the HTTP framework contract becomes more complex.
- Add durable audit persistence alongside `orders` if audit history matters.

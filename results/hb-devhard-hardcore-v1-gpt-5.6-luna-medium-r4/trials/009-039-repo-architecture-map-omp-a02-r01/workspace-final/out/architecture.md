# minisvc architecture

## Scope

`minisvc` is a small Python service that exposes order operations through an injected HTTP adapter and has a console bootstrap. The implementation in the fixture is authoritative over the older README design notes.

## Modules

- **`minisvc.config` (`config.py`)**: immutable `Settings`; reads `MINISVC_DB` and `MINISVC_READONLY` from an environment mapping.
- **`minisvc.models` (`models.py`)**: `Order` dataclass with `order_id`, `customer`, and `total_cents`.
- **`minisvc.storage.repo` (`storage/repo.py`)**: `OrderRepository` owns SQLite schema creation, inserts, and lookups. The `orders` table has a primary key on `order_id`.
- **`minisvc.audit` (`audit.py`)**: builds event dictionaries. Despite its name, it has no database/table or file persistence.
- **`minisvc.api.handlers` (`api/handlers.py`)**: converts payloads to `Order`, delegates persistence, and formats create/get results.
- **`minisvc.api.routes` (`api/routes.py`)**: binds `POST /orders` and `GET /orders/<order_id>` to handlers on a caller-supplied app.
- **`minisvc.cli` (`cli.py`)**: loads environment settings, creates a repository, initializes schema, and prints readiness.

`minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are package marker/export files, not business-logic modules.

## Entry points

- `minisvc.cli:main` is installed by the `minisvc` console script in `pyproject.toml`.
- `minisvc.api.routes:register_routes` is the HTTP adapter registration point.
- `minisvc.api.handlers:create_order` and `minisvc.api.handlers:get_order` are the endpoint handlers reached through registered routes.

## Data flow

### CLI startup

The console script calls `main(argv=None)`. `main` passes `os.environ` to `load_settings`, constructs `OrderRepository` with the selected database path, calls `init_schema`, prints `minisvc ready at ...`, and returns `0`. `argv` is accepted but unused.

### HTTP create order

An application first calls `register_routes(app, repo)`. A POST to `/orders` invokes `create_order(payload, repo)`. The handler indexes required keys, coerces `total_cents` with `int()`, constructs an `Order`, calls `repo.save`, constructs an in-memory `order_event(..., "created")`, and returns a response containing `status`, `order_id`, and `event`. Repository failures propagate; there is no retry layer.

GET follows the same route registration, calls `repo.get`, returns `{"status": "missing"}` when absent, or returns `order.__dict__` plus a transient `read` event when present.

## Storage and audit behavior

SQLite is opened independently per repository operation with `sqlite3.connect(self.database_path)`. `init_schema` creates only `orders`; `save` inserts; `get` selects. The default path is `orders.sqlite`, overridable with `MINISVC_DB`. SQLite transaction context managers provide commit/rollback behavior for each operation, but there is no migration, pooling, backup, or explicit durability policy.

`order_event` returns a dictionary only. Create and read events are included in API responses and are not written to an audit table. `Settings.readonly` is parsed, but `cli.main` does not pass it to `OrderRepository`, and the repository has no read-only enforcement. Writes therefore remain available even when `MINISVC_READONLY=1` is set.

## Risks and extension points

- **Durability and concurrency**: the local SQLite file is the sole store; there are no migrations, backup controls, connection configuration, or repository-level retry/locking policy. Extend `OrderRepository` behind its existing methods before adding a production storage policy.
- **Audit expectations**: `audit.py` is a response formatter rather than an audit sink. Add an explicit audit repository/table and define atomicity with order creation if durable audit evidence is required.
- **Configuration/runtime**: environment parsing is narrow (`== "1"` only), defaults to a relative path, and silently leaves readonly unused. Wire settings into a deliberate runtime composition root before adding flags or deployment assumptions.
- **Input validation**: `create_order` directly indexes payload keys and calls `int`; missing keys, malformed numbers, non-positive totals, oversized strings, and duplicate IDs are not translated into defined client errors. Add a validation boundary and map expected failures to the adapter's error model.
- **Read-only mode and retries**: README claims are contradicted by code; introducing these behaviors should be done at the repository/service boundary with tests for every write path, not by suppressing individual exceptions.

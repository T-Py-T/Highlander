# minisvc Architecture

## Overview

`minisvc` is a small Python service with two active runtime surfaces:

- A CLI bootstrap path in `minisvc.cli:main`.
- HTTP route registration in `minisvc.api.routes:register_routes`, which wires order handlers into an external app object.

The business logic is concentrated in `minisvc/api/handlers.py`, `minisvc/storage/repo.py`, `minisvc/config.py`, `minisvc/models.py`, and `minisvc/audit.py`. The package marker files `minisvc/api/__init__.py` and `minisvc/storage/__init__.py` are effectively empty, and `minisvc/__init__.py` only defines `__all__`; none of those files contain meaningful runtime logic.

## Modules

| Module | Role | Notes |
| --- | --- | --- |
| `minisvc.cli` | CLI bootstrap | Loads settings from environment, constructs the repository, initializes schema, prints readiness. |
| `minisvc.config` | Runtime configuration | Converts `MINISVC_DB` and `MINISVC_READONLY` into a frozen `Settings` object. |
| `minisvc.models` | Domain model | Defines the `Order` dataclass shared across layers. |
| `minisvc.audit` | Audit payload construction | Builds event dictionaries for responses; no storage side effects. |
| `minisvc.api.routes` | HTTP integration | Registers `POST /orders` and `GET /orders/<order_id>` callbacks on an app object. |
| `minisvc.api.handlers` | Request handling | Converts payloads to `Order`, calls storage, and shapes API responses. |
| `minisvc.storage.repo` | Persistence | Encapsulates SQLite schema creation, insert, and fetch operations. |

## Entry Points

- `minisvc.cli:main`
  Exposed through `pyproject.toml` as the `minisvc` console script.
- `minisvc.api.routes:register_routes`
  Intended to be called by an embedding HTTP app to attach endpoints.
- Routed handlers:
  `POST /orders` reaches `minisvc.api.handlers:create_order`.
  `GET /orders/<order_id>` reaches `minisvc.api.handlers:get_order`.

## Data Flow

### CLI startup flow

1. `minisvc.cli:main` reads `os.environ`.
2. `minisvc.config:load_settings` resolves the database path and readonly flag.
3. `OrderRepository` is instantiated with the configured database path.
4. `OrderRepository.init_schema` creates the `orders` table if needed.
5. The CLI prints a ready message and exits.

### HTTP create-order flow

1. `register_routes` binds the POST handler with a shared repository instance.
2. `create_order` pulls `order_id`, `customer`, and `total_cents` from the payload.
3. The handler constructs an `Order` dataclass.
4. `repo.save` inserts the order into SQLite.
5. `order_event` builds an audit-shaped response payload.
6. The handler returns `{"status": "created", "order_id": ..., "event": ...}`.

### HTTP read flow

1. `register_routes` binds the GET handler with the same repository instance.
2. `get_order` calls `repo.get(order_id)`.
3. If no row exists, the handler returns `{"status": "missing", "order_id": ...}`.
4. If a row exists, the handler serializes the dataclass with `order.__dict__` and attaches a read event from `order_event`.

## Storage

- Persistence is SQLite only, implemented directly in `minisvc/storage/repo.py`.
- The repository creates and uses one table: `orders(order_id text primary key, customer text not null, total_cents integer not null)`.
- Every repository method opens its own SQLite connection with `sqlite3.connect(self.database_path)`.
- Audit events are not persisted. `minisvc.audit:order_event` only creates a dictionary that is returned to callers.

## Risks And Extension Points

### Risks

- `MINISVC_READONLY` is parsed into settings but never enforced by the write path, so documented readonly behavior is absent.
- `create_order` performs no validation beyond key access and `int(...)` coercion. Missing keys, bad numeric input, duplicate primary keys, and SQLite failures will raise exceptions directly.
- There is no retry loop around SQLite writes despite the README design note describing one.
- Audit behavior is response-only; there is no durable audit table or write-ahead audit trail.
- The default database path is the relative file `orders.sqlite`, so runtime behavior depends on the process working directory.

### Extension points

- Enforce readonly mode in `minisvc.api.handlers:create_order` or `OrderRepository.save`.
- Add structured validation and error translation around payload parsing and SQLite exceptions.
- Introduce a real HTTP framework adapter around `register_routes` if request/response contracts need stronger typing.
- Add durable audit persistence alongside the existing `order_event` response payload.

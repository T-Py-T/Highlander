# minisvc architecture

## Scope

`minisvc` is a small Python service that exposes order operations through an application adapter and provides a CLI bootstrap command. The fixture's code is authoritative over the older design notes in `README.md`.

## Modules

- `minisvc.config` (`config.py`): immutable `Settings` plus `load_settings(env)`. Reads `MINISVC_DB` (default `orders.sqlite`) and `MINISVC_READONLY` (true only when equal to `1`). The readonly value is currently loaded but not enforced anywhere.
- `minisvc.models` (`models.py`): the `Order` dataclass (`order_id`, `customer`, `total_cents`).
- `minisvc.storage.repo` (`storage/repo.py`): `OrderRepository`, a thin SQLite data-access layer. It creates the `orders` table, inserts orders, and fetches one order by ID.
- `minisvc.audit` (`audit.py`): `order_event` creates a dictionary describing an order action. It does not persist an audit record.
- `minisvc.api.handlers` (`api/handlers.py`): create and read handlers. `create_order` builds an `Order`, saves it, and formats a response. `get_order` reads and formats either a missing or successful response.
- `minisvc.api.routes` (`api/routes.py`): `register_routes(app, repo)` binds `POST /orders` and `GET /orders/<order_id>` to handler callbacks.
- `minisvc.cli` (`cli.py`): `main(argv=None)` loads environment settings, constructs a repository, initializes the schema, and reports readiness.

`minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are package marker files. They contain no business logic and should not be treated as architecture modules beyond package structure.

## Entry points

The `pyproject.toml` script entry maps `minisvc` to `minisvc.cli:main`. The API integration entry point is `minisvc.api.routes:register_routes`; it expects an external `app` object with `post` and `get` methods and a repository supplied by the caller. Its registered endpoints are:

- `POST /orders` → `minisvc.api.handlers:create_order`
- `GET /orders/<order_id>` → `minisvc.api.handlers:get_order`

## Data flow

### CLI startup

`main` → `load_settings(os.environ)` → `OrderRepository(settings.database_path)` → `init_schema()` → readiness print. `Settings.readonly` is not passed to the repository or checked by any write path.

### HTTP create order

`POST /orders` callback → `create_order(payload, repo)` → required payload indexing and `int(total_cents)` → `Order` construction → `repo.save(order)` → `order_event(order, "created")` → response `{status, order_id, event}`. The event is response data only. SQLite writes use parameterized SQL and a context-managed connection.

The read path is similar: `GET /orders/<order_id>` → `repo.get` → either a `missing` response or an `ok` response containing `order.__dict__` and an in-memory `read` event.

## Storage

SQLite is the only persistence mechanism. `OrderRepository` opens a fresh connection for each schema, save, or get operation. The database path is configurable through `MINISVC_DB`; absent configuration uses a relative `orders.sqlite`, so the effective location depends on the process working directory. The schema has one `orders` table with a primary key on `order_id` and non-null `customer` and `total_cents` columns. There is no audit table, migration layer, explicit durability policy, or repository retry loop in this code.

## Risks and extension points

- **Readonly gap:** `load_settings` records readonly but `create_order` and `OrderRepository.save` never receive or enforce it. A caller expecting the README contract can still write.
- **Failure handling:** malformed/missing payload fields, invalid integer conversion, SQLite errors, and duplicate IDs propagate from the handler; there is no HTTP error translation or retry behavior.
- **Audit gap:** `order_event` is ephemeral and returned to clients. There is no durable audit trail or transaction tying an audit record to an order write.
- **Runtime configuration:** relative database paths and direct `os.environ` access make deployment context significant. `main` also ignores `argv`.
- **API boundary:** `create_order` performs only basic key access and integer coercion. Add explicit validation and adapter-level error mapping before exposing it to untrusted clients.

Natural extension points are the repository boundary for transactions/migrations and the handler boundary for validation and response error policy. Readonly enforcement should be designed into that boundary rather than inferred from configuration alone; durable auditing should share the order-write transaction if audit completeness is required.

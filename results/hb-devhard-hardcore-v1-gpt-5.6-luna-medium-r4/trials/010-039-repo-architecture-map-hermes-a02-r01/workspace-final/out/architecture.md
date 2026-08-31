# minisvc architecture

## Purpose

`minisvc` is a small order service. The repository contains a CLI bootstrap path and a framework-neutral HTTP adapter. The implementation, rather than the older README design notes, is authoritative.

## Modules

- `minisvc/config.py` — `Settings` and `load_settings`; reads `MINISVC_DB` and `MINISVC_READONLY`.
- `minisvc/models.py` — the `Order` dataclass (`order_id`, `customer`, `total_cents`).
- `minisvc/storage/repo.py` — `OrderRepository`; initializes and accesses a SQLite `orders` table.
- `minisvc/audit.py` — `order_event`; creates event dictionaries in memory.
- `minisvc/api/handlers.py` — `create_order` and `get_order`; maps request data to domain objects and response dictionaries.
- `minisvc/api/routes.py` — `register_routes`; wires POST `/orders` and GET `/orders/<order_id>` to handlers.
- `minisvc/cli.py` — executable bootstrap.

`minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are package marker files, not business-logic modules. The fixture has no separate HTTP server process or framework implementation; an external app supplies `app` to `register_routes`.

## Entry points

- `minisvc.cli:main` is exposed as the `minisvc` console script by `pyproject.toml`.
- `minisvc.api.routes:register_routes(app, repo)` is the HTTP adapter setup entry point.
- `register_routes` wires `minisvc.api.handlers:create_order` to POST `/orders` and `get_order` to GET `/orders/<order_id>`.

## Data flow

### CLI startup

`main` passes `os.environ` to `load_settings`, constructs `OrderRepository(settings.database_path)`, calls `init_schema()`, prints a readiness message, and returns zero. Although `Settings` carries `readonly`, `main` does not enforce it and the repository never receives it.

### HTTP create order

After route registration, a POST payload reaches `create_order`. Required keys are indexed directly, and `total_cents` is converted with `int()`. An `Order` is constructed, saved through `OrderRepository.save`, and returned with status, order ID, and an `order_event` dictionary. There is no explicit validation layer, retry wrapper, or error-to-HTTP response mapping.

For a GET, `get_order` calls `repo.get`. A missing row returns `status: missing`; an existing row is serialized from `order.__dict__` and accompanied by a read event.

## Storage

SQLite is opened independently for each repository operation with `sqlite3.connect(self.database_path)`. `init_schema` creates only the `orders` table with a primary key on `order_id` and non-null `customer` and `total_cents`. `save` executes one parameterized INSERT; `get` executes one parameterized SELECT. The database path defaults to the relative file `orders.sqlite`, so its location depends on the process working directory.

Audit data is not stored in SQLite: `minisvc.audit.order_event` returns a plain dictionary and no audit table is created by `init_schema`.

## Risks and extension points

- **Readonly enforcement:** `load_settings` parses `MINISVC_READONLY`, but no write path checks `Settings.readonly`; add an explicit policy boundary before `save` and test CLI/API behavior.
- **Durability and concurrency:** there is no migration/versioning, connection policy, backup strategy, or retry/transaction policy beyond SQLite context-manager commit/rollback behavior. The relative default path can select an unexpected database.
- **Input validation:** missing keys raise `KeyError`; malformed totals raise `ValueError`; duplicate IDs surface raw SQLite errors. Add request validation and consistent error responses before constructing `Order`.
- **Audit semantics:** events are response values only, so they can be lost and are not an audit trail. A durable audit repository/table would be an extension point, ideally coordinated transactionally with order writes.
- **HTTP integration:** route callbacks are lambdas around a supplied `app`; framework error handling and request lifecycle are external concerns.
- **Retry behavior:** `OrderRepository.save` is a single insert, with no retry despite the README claim.

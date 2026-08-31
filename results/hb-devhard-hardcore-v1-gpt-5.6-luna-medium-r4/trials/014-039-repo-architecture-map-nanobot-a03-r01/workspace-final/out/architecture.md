# minisvc architecture

## Scope

`minisvc` is a small order service with a CLI bootstrap and an HTTP adapter. The fixture README explicitly says the implementation is authoritative over older design notes. The package marker files (`minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py`) contain no business logic and should not be treated as runtime modules.

## Modules

- `minisvc.cli:main` (`minisvc/cli.py`) is the executable bootstrap declared by `pyproject.toml`. It loads environment settings, constructs `OrderRepository`, initializes the schema, prints readiness, and returns 0.
- `minisvc.config:load_settings` (`minisvc/config.py`) maps `MINISVC_DB` to a database path (default `orders.sqlite`) and recognizes `MINISVC_READONLY=1`. `Settings` is a frozen dataclass, but the setting is not consumed by the CLI, repository, or handlers.
- `minisvc.models.Order` (`minisvc/models.py`) is the shared mutable dataclass with `order_id`, `customer`, and `total_cents`.
- `minisvc.storage.repo.OrderRepository` (`minisvc/storage/repo.py`) owns SQLite schema creation, inserts, and point reads. Each operation opens a connection with a context manager.
- `minisvc.audit.order_event` (`minisvc/audit.py`) creates an event dictionary. Despite its name, it does not write to storage.
- `minisvc.api.handlers` contains `create_order` and `get_order`, the application-level create/read behavior.
- `minisvc.api.routes:register_routes` (`minisvc/api/routes.py`) attaches `POST /orders` and `GET /orders/<order_id>` to lambdas that capture a repository.

## Entry points

The packaging entry point is `minisvc.cli:main`, exposed as the `minisvc` command. API setup enters through `minisvc.api.routes:register_routes`; it registers `POST /orders` and `GET /orders/<order_id>`. No web framework or server loop is present in this repository, so a host application must supply `app` and invoke route registration.

## Data flow

At startup, `main` reads `os.environ`, creates a repository, and calls `init_schema`. For creation, the HTTP adapter passes a payload to `create_order`; the handler indexes required keys, converts `total_cents` using `int`, constructs `Order`, calls `repo.save`, then returns a status, ID, and event dictionary. Reads call `repo.get`; a found row becomes an `Order` and is returned as `order.__dict__` with a read event. Missing rows return a `missing` response.

The event is response data only. There is no call from `order_event` to a persistence API and no audit table in `OrderRepository.init_schema`.

## Storage

SQLite is the only persistence layer. `OrderRepository` uses the configured path and creates an `orders` table with a primary-key `order_id`, non-null `customer`, and non-null integer `total_cents`. Inserts use parameterized SQL. There is no explicit transaction/retry policy beyond SQLite connection context-manager commit/rollback behavior, no migrations, no connection pool, and no audit storage.

## Risks and extension points

- Read-only enforcement is incomplete: `load_settings` records `Settings.readonly`, but `main` and the handlers never inspect it. A future write guard should be applied consistently to schema initialization and `create_order` (and ideally be tested at the repository boundary).
- The README's claimed two retries for failed SQLite writes are not implemented: `create_order` calls `repo.save` once and propagates exceptions. Add a narrowly scoped retry policy around transient SQLite failures with bounded attempts and tests.
- Audit durability is absent: `order_event` only returns a dict. Introduce an explicit audit repository/table and define ordering and transaction semantics if durable audit is required.
- Input errors are not translated: missing payload keys raise `KeyError`, and invalid/non-integral totals raise `ValueError`; there is no schema validation, length/range policy, or HTTP error mapping in `routes.py`.
- Duplicate IDs and database errors propagate from `save`; the API adapter has no visible error contract.
- The relative default `orders.sqlite` depends on the process working directory. Prefer an explicit deployment path and validate configuration at startup.

The safest extension points are the handler/repository boundary, a repository-level write policy, and an explicit adapter error-mapping layer. Keep the marker `__init__.py` files empty unless package metadata is genuinely needed.

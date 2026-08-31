# minisvc architecture

`minisvc` is a small Python order service backed by SQLite. The active runtime code is in `cli.py`, `config.py`, `models.py`, `api/routes.py`, `api/handlers.py`, `storage/repo.py`, and `audit.py`. The three `__init__.py` files are package markers (one sets `__all__`; two are empty), not business logic.

## Modules

- **`minisvc.cli`** — `main` bootstraps the service.
- **`minisvc.config`** — `Settings` and `load_settings`; reads `MINISVC_DB` (default `orders.sqlite`) and `MINISVC_READONLY` (true only for `"1"`).
- **`minisvc.models`** — `Order` dataclass with `order_id`, `customer`, and `total_cents`.
- **`minisvc.api.routes`** — `register_routes(app, repo)` binds `POST /orders` and `GET /orders/<order_id>`.
- **`minisvc.api.handlers`** — `create_order` and `get_order` request handlers.
- **`minisvc.storage.repo`** — `OrderRepository` creates, inserts, and selects the SQLite `orders` table.
- **`minisvc.audit`** — `order_event` builds event dictionaries in memory.

## Entry points

The console script `minisvc` maps to `minisvc.cli:main` in `pyproject.toml`. HTTP integration begins at `minisvc.api.routes:register_routes`; it expects an app object with `.post` and `.get`. No concrete HTTP framework or server is included in this repository.

## Data flow

### CLI startup

1. `main` calls `load_settings(os.environ)`.
2. It constructs `OrderRepository(settings.database_path)`.
3. `init_schema` opens SQLite and creates `orders` if needed.
4. The CLI prints a ready message and returns `0`.

### HTTP create order

`register_routes` maps POST `/orders` to `create_order`. The handler directly indexes `order_id`, `customer`, and `total_cents`, casts the total with `int`, constructs `Order`, calls `repo.save`, and returns a `created` response. `save` inserts one row. `order_event` adds a created-event dictionary to the response; it does not write an audit record.

Reads follow the same adapter: `get_order` calls `repo.get`, returns `missing` for no row, or returns `ok`, the order dictionary, and an in-memory read event.

## Storage

`OrderRepository` uses `sqlite3.connect(self.database_path)` for each operation and a primary key on `order_id`. There is no migration layer, backup policy, explicit timeout, retry loop, duplicate-ID mapping, or audit table. Transactions rely on SQLite connection context managers.

## Documentation gaps, risks, and extension points

README design notes claim that `MINISVC_READONLY=1` blocks writes, failed writes retry twice, and audit events go to a durable table. The implementation contradicts all three: `load_settings` only parses readonly; `create_order` and `save` always write; `save` runs once; and `order_event` only returns a dict while `init_schema` creates only `orders`. The README says code is authoritative.

Main risks are accidental writes in supposed readonly mode, lost audit history, lock/disk failures without retry or recovery guidance, a relative database path that varies with the working directory, and unstable API errors (`KeyError`, `ValueError`, or `TypeError`) for malformed payloads. The safest extension points are a repository policy for readonly and retries, schema-backed audit persistence, explicit request validation/error translation in `api.handlers`, and a migration/configuration layer. Add tests before changing these contracts.

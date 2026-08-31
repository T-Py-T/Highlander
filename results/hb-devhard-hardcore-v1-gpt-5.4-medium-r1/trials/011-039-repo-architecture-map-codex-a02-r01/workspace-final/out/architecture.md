# minisvc Architecture Summary

## What is active runtime code

Active runtime modules:

- `minisvc.cli` bootstraps local startup and schema initialization.
- `minisvc.config` loads environment-based settings.
- `minisvc.api.routes` attaches HTTP endpoints to handlers.
- `minisvc.api.handlers` implements create/read order behavior.
- `minisvc.audit` shapes audit event dictionaries for responses.
- `minisvc.storage.repo` is the only persistence adapter.
- `minisvc.models` defines the `Order` dataclass used across layers.

Do not treat package marker files as business logic:

- `minisvc/api/__init__.py` and `minisvc/storage/__init__.py` are empty markers.
- `minisvc/__init__.py` only exposes `__all__` and does not participate in runtime flow.

## Entry points

- CLI: `minisvc.cli:main`, exposed by the `minisvc` console script in `pyproject.toml`.
- HTTP registration hook: `minisvc.api.routes:register_routes`.
- Effective handler entry points once routes are registered:
  - `minisvc.api.handlers:create_order` for `POST /orders`
  - `minisvc.api.handlers:get_order` for `GET /orders/<order_id>`

## Module relationships

The architecture is shallow and linear:

- `cli` depends on `config` and `storage.repo`.
- `api.routes` depends on `api.handlers`.
- `api.handlers` depends on `models`, `audit`, and `storage.repo`.
- `storage.repo` depends on `models` and the standard `sqlite3` module.

There is no service layer between the HTTP handlers and the repository. Handlers construct domain objects directly and call repository methods directly.

## Runtime flow

### CLI startup

1. The `minisvc` console script invokes `minisvc.cli:main`.
2. `main` reads `MINISVC_DB` and `MINISVC_READONLY` through `load_settings(os.environ)`.
3. `main` creates `OrderRepository(settings.database_path)`.
4. `main` calls `repo.init_schema()` to create the `orders` table if needed.
5. `main` prints the database location and exits.

Important detail: `MINISVC_READONLY` is parsed into `Settings`, but startup does nothing with it beyond storing the flag.

### HTTP create-order flow

1. An external app calls `register_routes(app, repo)`.
2. `POST /orders` is wired to `create_order(payload, repo)`.
3. `create_order` reads three required payload keys and coerces `total_cents` with `int(...)`.
4. The handler creates an `Order` dataclass instance.
5. The handler calls `repo.save(order)`, which inserts a row into SQLite.
6. The handler builds an event dictionary with `order_event(order, "created")`.
7. The response includes `status`, `order_id`, and the in-memory event object.

The read path is similar: `GET /orders/<order_id>` calls `repo.get`, returns `missing` if no row exists, otherwise returns the order plus a read event.

## Data flow and storage

- Input arrives as unvalidated dictionaries in the HTTP layer.
- The only domain object is `Order(order_id, customer, total_cents)`.
- Persistence is a single SQLite table: `orders(order_id text primary key, customer text not null, total_cents integer not null)`.
- Every repository operation opens a new SQLite connection with a context manager.
- Audit data is not stored separately. `minisvc.audit.order_event` only returns a dictionary that is embedded in API responses.

## Configuration

Environment variables:

- `MINISVC_DB`: path to the SQLite file. Defaults to `orders.sqlite`.
- `MINISVC_READONLY`: parsed as a boolean flag in `Settings.readonly`.

Only `MINISVC_DB` affects behavior. The readonly flag is currently dead configuration because no write path checks it.

## Risks and extension points

Main risks:

- Readonly mode is documented but unenforced, so operators could believe writes are blocked when they are not.
- `create_order` has no retry logic and no error translation; SQLite failures will propagate as exceptions.
- Audit behavior is response-only, so there is no durable audit history.
- Request validation is minimal; missing keys, non-numeric totals, or duplicate order ids will raise exceptions instead of returning structured API errors.
- Schema initialization happens only in the CLI path. An HTTP host that skips `cli.main` must initialize the database elsewhere.

Best extension points:

- Add a small service layer between handlers and repository methods to centralize validation, readonly enforcement, retries, and audit persistence.
- Extend `OrderRepository` with explicit error handling and migration/schema management.
- Replace the lambda route adapters with named callables if the framework integration needs better observability or testability.

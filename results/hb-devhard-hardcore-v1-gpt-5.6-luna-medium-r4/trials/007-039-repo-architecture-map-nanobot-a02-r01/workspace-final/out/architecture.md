# minisvc architecture

## Scope

`minisvc` is a small order service with a CLI bootstrap and an injected HTTP adapter. The fixture's implementation is authoritative over the older design notes in `README.md`.

## Modules

- `minisvc/config.py`: `load_settings(env)` maps `MINISVC_DB` (default `orders.sqlite`) and `MINISVC_READONLY` to the frozen `Settings` dataclass. The readonly value is currently not consumed by any write path.
- `minisvc/models.py`: the `Order` dataclass (`order_id`, `customer`, `total_cents`).
- `minisvc/storage/repo.py`: `OrderRepository` opens SQLite connections per operation, creates the `orders` table, inserts orders, and fetches orders.
- `minisvc/api/handlers.py`: `create_order` and `get_order` coordinate model construction, repository calls, and response dictionaries.
- `minisvc/api/routes.py`: `register_routes(app, repo)` wires `POST /orders` and `GET /orders/<order_id>` to handlers. The HTTP framework/application is not included in this fixture.
- `minisvc/audit.py`: creates event dictionaries only; it is not a persistence layer.
- `minisvc/cli.py`: `minisvc.cli:main` loads configuration, initializes the schema, and prints readiness.

`minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are package marker/export files, not business-logic modules.

## Entry points and runtime flow

The declared console script is `minisvc = minisvc.cli:main`. The API registration entry point is `minisvc.api.routes:register_routes`.

CLI startup: `main` -> `load_settings(os.environ)` -> `OrderRepository(database_path)` -> `init_schema()` -> readiness print. It does not start an HTTP server.

HTTP create flow: an external app registers routes -> `POST /orders` lambda -> `create_order(payload, repo)` -> `Order(...)` -> `repo.save(order)` -> `order_event(order, "created")` -> response dictionary. Required keys are accessed directly and `total_cents` is converted with `int`; failures propagate. The event is returned but not stored.

The read flow is analogous: `GET /orders/<order_id>` -> `get_order` -> `repo.get`; it returns `missing` when absent, otherwise the order's `__dict__` and a transient read event.

## Data flow and storage

Input payloads become an `Order`, then `OrderRepository.save` executes a parameterized SQLite INSERT into `orders`. Each repository method opens its own connection with `sqlite3.connect`; the context manager commits successful writes and closes the connection. `get` performs a parameterized SELECT and reconstructs an `Order`. The database path is configurable through `MINISVC_DB`, but no migrations, connection pooling, retry layer, or audit table exists.

## Documentation/code discrepancies

The README claims that `MINISVC_READONLY=1` blocks writes, that create retries failed SQLite writes twice, and that audit events are durable. In code, `Settings.readonly` is merely loaded, `create_order` calls `save` once, and `order_event` returns a dictionary without persistence. See `doc_code_discrepancies.csv` for evidence and impact.

## Risks and extension points

- Storage durability and concurrency are delegated to per-call SQLite connections with no explicit operational policy, migration mechanism, backup handling, or retry handling.
- The readonly setting is not enforced, so deployments relying on the README contract can accept writes.
- API validation is minimal: missing keys raise `KeyError`, malformed totals raise `ValueError`/`TypeError`, and there are no checks for empty strings, negative totals, payload shape, or duplicate IDs.
- Audit output is transient and can be lost; it also exposes the order total in the returned response.
- A natural extension is an application factory that creates the repository, calls `init_schema`, registers routes, and explicitly passes/enforces settings. Additional safe extension points are a validation boundary in `create_order`, a repository retry policy, migrations, and a dedicated audit repository/table.

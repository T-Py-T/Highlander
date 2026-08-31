# minisvc architecture

## What this repo does
`minisvc` is a small Python service slice with two front doors:
- a CLI bootstrap command at `minisvc.cli:main`
- an HTTP route registration hook at `minisvc.api.routes:register_routes`

The active runtime code is in `minisvc/cli.py`, `minisvc/config.py`, `minisvc/models.py`, `minisvc/audit.py`, `minisvc/api/handlers.py`, `minisvc/api/routes.py`, and `minisvc/storage/repo.py`.

Do not treat `minisvc/__init__.py`, `minisvc/api/__init__.py`, or `minisvc/storage/__init__.py` as business logic. They are package markers or tiny export files.

## Module map
- `minisvc/cli.py` — CLI bootstrap. Loads settings, builds `OrderRepository`, creates the schema, prints readiness.
- `minisvc/config.py` — immutable `Settings` dataclass and env loading for `MINISVC_DB` and `MINISVC_READONLY`.
- `minisvc/models.py` — `Order` dataclass.
- `minisvc/audit.py` — builds audit event dictionaries from an `Order` and an action name.
- `minisvc/api/handlers.py` — request handlers for create and read order flows.
- `minisvc/api/routes.py` — wires handler lambdas onto an injected HTTP app.
- `minisvc/storage/repo.py` — SQLite persistence layer for schema init, insert, and lookup.

## Entry points
- `minisvc.cli:main`
  - exposed by `pyproject.toml` as the `minisvc` console script
  - local role: set up the DB file and table
- `minisvc.api.routes:register_routes`
  - not a server by itself
  - meant to be called by an external app bootstrap that supplies `app` and `repo`
- Request handlers behind the registered routes:
  - `minisvc.api.handlers:create_order`
  - `minisvc.api.handlers:get_order`

## Data flow
### CLI startup flow
1. `minisvc.cli:main` reads process env through `minisvc.config:load_settings`.
2. `load_settings` resolves `database_path` from `MINISVC_DB` or defaults to `orders.sqlite`.
3. `main` builds `OrderRepository(settings.database_path)`.
4. `OrderRepository.init_schema()` opens SQLite and creates the `orders` table if needed.
5. `main` prints `minisvc ready at ...` and exits.

### HTTP create-order flow
1. `minisvc.api.routes:register_routes` binds `POST /orders` to `create_order(payload, repo)`.
2. `minisvc.api.handlers:create_order` reads `order_id`, `customer`, and `total_cents` straight from the payload.
3. It constructs an `Order` dataclass and calls `repo.save(order)`.
4. `OrderRepository.save` opens SQLite and runs a plain `INSERT` into `orders`.
5. `minisvc.audit:order_event` builds a response event dict.
6. The handler returns `{"status": "created", ...}`.

### HTTP read-order flow
1. `register_routes` binds `GET /orders/<order_id>` to `get_order(order_id, repo)`.
2. `get_order` calls `repo.get(order_id)`.
3. `OrderRepository.get` selects one row and returns `Order(*row)` or `None`.
4. The handler returns either `{"status": "missing"}` or `{"status": "ok", "order": order.__dict__, ...}`.

## Storage
- Storage lives in a single SQLite database file.
- The file path comes from `MINISVC_DB` or falls back to `orders.sqlite` in the current working directory.
- The only schema in code is:
  - `orders(order_id text primary key, customer text not null, total_cents integer not null)`
- There is no audit table in the code.
- Each repo method opens a fresh `sqlite3.connect(...)` context.

## Notable design facts
- `MINISVC_READONLY` is parsed into `Settings.readonly`, but no runtime path checks it before writes.
- `create_order` does not retry failed writes.
- Audit data is returned in API responses, not persisted.
- The HTTP framework is deliberately abstract here; `register_routes` only assumes `app.post(...)` and `app.get(...)`.

## Risks and extension points
### Risks
- **Write guard gap**: docs mention readonly mode, but `create_order` and `OrderRepository.save` never check `Settings.readonly`.
- **Thin input validation**: missing keys, bad integers, duplicate IDs, and negative totals can turn into raw exceptions or bad data.
- **Audit gap**: no durable audit storage exists even though response events are built.
- **Path surprise**: defaulting to relative `orders.sqlite` can create data in an unexpected working directory.
- **Operational limits**: no retry policy, no explicit transaction handling beyond sqlite context defaults, and no migration path beyond one `create table if not exists` call.

### Extension points
- Pass a richer app object into `minisvc.api.routes:register_routes` to host the handlers in a real server.
- Add validation and error mapping around `minisvc.api.handlers:create_order`.
- Enforce readonly mode either in handlers, the repository, or both.
- Add an audit repository and schema if durable audit history matters.
- Replace or wrap `OrderRepository` if you need another backing store.

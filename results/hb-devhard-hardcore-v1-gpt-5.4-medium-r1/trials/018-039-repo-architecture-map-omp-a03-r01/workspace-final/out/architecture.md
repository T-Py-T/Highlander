# minisvc architecture

## Scope
This fixture is a tiny order service split into a CLI bootstrap path, a route-registration layer, request handlers, and a SQLite repository. The runtime code is under `minisvc/`. The `__init__.py` files are package markers and exports; they are not business-logic modules.

## Active runtime modules
- `minisvc/cli.py` — console startup. Loads settings, builds `OrderRepository`, initializes schema, prints readiness.
- `minisvc/config.py` — `Settings` dataclass and `load_settings(env)` for `MINISVC_DB` and `MINISVC_READONLY`.
- `minisvc/models.py` — `Order` dataclass shared across layers.
- `minisvc/audit.py` — `order_event(order, action)` helper that builds response event dictionaries.
- `minisvc/api/routes.py` — `register_routes(app, repo)` wires `POST /orders` and `GET /orders/<order_id>`.
- `minisvc/api/handlers.py` — `create_order` and `get_order`; this is where payload coercion and response shaping happen.
- `minisvc/storage/repo.py` — SQLite persistence for the `orders` table.

## Package markers and dead-simple files
- `minisvc/__init__.py` only exports `config` and `models`.
- `minisvc/api/__init__.py` and `minisvc/storage/__init__.py` are empty package markers.
- `pyproject.toml` only declares the package and console script entry point.

## Entry points
- `minisvc.cli:main` — console script published as `minisvc` in `pyproject.toml`.
- `minisvc.api.routes:register_routes` — route registrar for the HTTP adapter.
- Handler entry points behind the routes: `minisvc.api.handlers:create_order` and `minisvc.api.handlers:get_order`.

## Data flow
### CLI startup flow
1. `minisvc.cli:main` calls `load_settings(os.environ)`.
2. `minisvc.config:load_settings` maps env vars into `Settings(database_path, readonly)`.
3. `main` instantiates `OrderRepository(settings.database_path)`.
4. `repo.init_schema()` creates the `orders` table if needed.
5. `main` prints `minisvc ready at ...` and exits.

### HTTP create-order flow
1. An external app calls the lambda registered for `POST /orders` in `register_routes(app, repo)`.
2. `create_order(payload, repo)` reads `order_id`, `customer`, and `total_cents` directly from the payload dict.
3. `create_order` builds an `Order` dataclass and coerces `total_cents` with `int()`.
4. `repo.save(order)` inserts the row into SQLite.
5. `order_event(order, "created")` builds an in-memory event dict.
6. The handler returns `{"status": "created", "order_id": ..., "event": ...}`.

### HTTP read-order flow
1. The `GET /orders/<order_id>` lambda calls `get_order(order_id, repo)`.
2. `repo.get(order_id)` queries SQLite.
3. Missing rows return `{"status": "missing", "order_id": ...}`.
4. Found rows return `{"status": "ok", "order": order.__dict__, "event": order_event(order, "read")}`.

## Storage
- Only one durable table exists: `orders(order_id text primary key, customer text not null, total_cents integer not null)` in SQLite.
- `OrderRepository` opens a new `sqlite3.connect()` context for schema init, save, and get.
- The audit helper does not persist anything; it only returns dictionaries included in handler responses.
- Default storage path is the relative file `orders.sqlite` unless `MINISVC_DB` is set.

## Risks and extension points
### Risks
- `MINISVC_READONLY` is parsed into settings but never enforced on write paths. The README claim is stale.
- `create_order` has no input validation layer; missing keys raise `KeyError`, bad numeric values raise `ValueError`, and duplicate IDs bubble `sqlite3.IntegrityError`.
- There is no retry loop around SQLite writes despite the README design note.
- Audit events are not durable; there is no audit table or repository method for them.
- No checked-in automated tests were found in the fixture repository.

### Extension points
- Add an actual HTTP app wrapper around `register_routes` if the service needs a runnable API process.
- Introduce request validation and domain-level error mapping in `minisvc/api/handlers.py`.
- Enforce readonly centrally, either in handlers before `repo.save()` or inside the repository interface.
- Add a durable audit store if audit history matters operationally.
- Expand `OrderRepository` behind a narrower interface if more storage backends are expected.

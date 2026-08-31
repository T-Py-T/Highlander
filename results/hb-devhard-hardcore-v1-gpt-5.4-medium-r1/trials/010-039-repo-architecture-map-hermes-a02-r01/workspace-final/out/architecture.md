# minisvc architecture summary

## What this repository is
`minisvc` is a tiny Python service skeleton with two runtime surfaces:
- a console bootstrap command exposed as `minisvc.cli:main`
- an HTTP-style adapter registration function exposed as `minisvc.api.routes:register_routes`

The active runtime code lives in `minisvc/cli.py`, `minisvc/config.py`, `minisvc/models.py`, `minisvc/audit.py`, `minisvc/storage/repo.py`, `minisvc/api/handlers.py`, and `minisvc/api/routes.py`.

Do not over-interpret package marker files:
- `minisvc/__init__.py` only defines `__all__`
- `minisvc/api/__init__.py` is effectively empty
- `minisvc/storage/__init__.py` is effectively empty

## Module map
- `minisvc.cli`: bootstrap command that loads config, creates `OrderRepository`, initializes schema, and prints readiness.
- `minisvc.config`: `Settings` dataclass and `load_settings(env)` environment parser.
- `minisvc.models`: `Order` dataclass shared across handlers and storage.
- `minisvc.audit`: `order_event(order, action)` helper that creates audit-shaped response metadata.
- `minisvc.storage.repo`: SQLite persistence layer with `init_schema`, `save`, and `get`.
- `minisvc.api.handlers`: request handlers `create_order` and `get_order`.
- `minisvc.api.routes`: adapter layer that wires routes onto a caller-supplied `app` object.
- `pyproject.toml`: packaging metadata and console-script registration.

## Entry points
- `minisvc.cli:main`
  - Declared in `pyproject.toml` under `[project.scripts]`.
  - Initializes local SQLite storage and exits.
- `minisvc.api.routes:register_routes`
  - Accepts an `app` and a prebuilt `repo`.
  - Registers POST `/orders` and GET `/orders/<order_id>` using lambdas that close over `repo`.
- Handler-level execution targets:
  - `minisvc.api.handlers:create_order`
  - `minisvc.api.handlers:get_order`

## Data flow
### CLI startup flow
1. `minisvc` executes `minisvc.cli:main`.
2. `main()` reads `MINISVC_DB` and `MINISVC_READONLY` through `load_settings(os.environ)`.
3. `main()` builds `OrderRepository(settings.database_path)`.
4. `main()` runs `repo.init_schema()`.
5. The command prints the resolved database path and exits with `0`.

Important nuance: `readonly` is parsed into `Settings` but the CLI does not enforce it; startup still initializes schema and can create a database file.

### HTTP create-order flow
1. A host app calls `register_routes(app, repo)`.
2. POST `/orders` dispatches to `create_order(payload, repo)`.
3. `create_order()` requires `order_id`, `customer`, and `total_cents` keys in the payload.
4. It constructs an `Order` and coerces `total_cents` with `int(...)`.
5. `repo.save(order)` inserts a row into SQLite.
6. `order_event(order, "created")` builds an event dict.
7. The response is a simple dict with `status`, `order_id`, and `event`.

### HTTP get-order flow
1. GET `/orders/<order_id>` dispatches to `get_order(order_id, repo)`.
2. `repo.get(order_id)` looks up the row in SQLite.
3. Missing rows return `{"status": "missing", "order_id": ...}`.
4. Found rows return `{"status": "ok", "order": order.__dict__, "event": ...}`.

## Storage
- Storage engine: SQLite via the standard-library `sqlite3` module.
- Database path source: `MINISVC_DB`, defaulting to `orders.sqlite` in the process working directory.
- Schema management: `OrderRepository.init_schema()` creates one `orders` table.
- Persisted business data: `order_id`, `customer`, `total_cents`.
- Audit storage: none. Audit information is generated in-memory as response payloads only.

## Configuration and runtime assumptions
- No framework dependency is declared. `register_routes()` assumes the caller provides an `app` object with `.post(...)` and `.get(...)` methods that accept a path and callable.
- `MINISVC_READONLY` is parsed but unused outside configuration loading.
- Errors from missing payload keys, invalid integer coercion, duplicate primary keys, or SQLite failures are not caught and will bubble to the caller.

## Risks and extension points
### Risks
- Readonly mode is documented but not enforced in handlers or repository code.
- SQLite writes have no retry logic despite the README claim.
- Audit events are not durable; they are returned in responses but never persisted.
- Input validation is minimal; payload shape and numeric conversion rely on raw dict access and `int(...)`.
- The default relative database path can place data in unexpected directories depending on process CWD.

### Extension points
- Add a service layer between handlers and repository for business rules like readonly enforcement, retries, or richer validation.
- Replace `order_event()`'s transient dict with a persisted audit sink if durable auditing matters.
- Inject a real web framework adapter around `register_routes()` or replace lambda routes with framework-native handlers.
- Expand `Settings` for explicit database URI, timeout, or environment-specific behavior.
- Add tests around handler error paths, duplicate inserts, and configuration handling.

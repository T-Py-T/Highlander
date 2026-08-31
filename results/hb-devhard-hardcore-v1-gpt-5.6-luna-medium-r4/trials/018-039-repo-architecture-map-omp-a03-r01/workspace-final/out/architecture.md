# minisvc architecture

## Scope

`minisvc` is a small order service with a console bootstrap and an HTTP adapter. The fixture README says the code is authoritative when the older design notes disagree. `minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are package marker/export files, not business-logic modules; the active runtime is in the seven Python modules below.

## Modules

- **`minisvc.cli` (`minisvc/cli.py`)** — console-script entry point. Loads settings, constructs `OrderRepository`, initializes the schema, prints readiness, and returns zero. It does not launch an HTTP server.
- **`minisvc.config` (`minisvc/config.py`)** — frozen `Settings` dataclass plus `load_settings`. Reads `MINISVC_DB` (default `orders.sqlite`) and `MINISVC_READONLY` (`"1"` means true).
- **`minisvc.models` (`minisvc/models.py`)** — `Order` dataclass with `order_id`, `customer`, and integer `total_cents`.
- **`minisvc.storage.repo` (`minisvc/storage/repo.py`)** — SQLite repository. `init_schema` creates `orders`; `save` inserts; `get` selects by ID. Each operation opens its own SQLite connection with a context manager.
- **`minisvc.api.routes` (`minisvc/api/routes.py`)** — registers `POST /orders` and `GET /orders/<order_id>` against an injected `app` and repository.
- **`minisvc.api.handlers` (`minisvc/api/handlers.py`)** — application handlers. `create_order` maps a payload to an `Order`, saves it, and returns a response event. `get_order` maps a repository result to either a missing or successful response.
- **`minisvc.audit` (`minisvc/audit.py`)** — constructs an order event dictionary. Despite its name, it has no persistence or logging sink.

## Entry points

The packaging entry point is `minisvc = minisvc.cli:main` in `pyproject.toml`. API setup is `minisvc.api.routes:register_routes`; it binds `POST /orders` to `minisvc.api.handlers:create_order` and `GET /orders/<order_id>` to `get_order`. The HTTP framework is intentionally abstract: `register_routes` expects an `app` exposing `post` and `get`, plus an injected repository.

## Data flow

### CLI startup

`minisvc.cli:main` → `load_settings(os.environ)` → `OrderRepository(settings.database_path)` → `repo.init_schema()` → readiness print. `readonly` is loaded into `Settings` but is not consulted by `main` or the repository.

### HTTP create order

`register_routes(app, repo)` installs a POST callback → `create_order(payload, repo)` indexes `order_id` and `customer`, converts `total_cents` using `int`, and constructs `Order` → `OrderRepository.save` inserts into SQLite → `order_event(order, "created")` builds a dictionary → response returns `status`, `order_id`, and the event. There is no retry loop and no separate audit write.

The read path is analogous: `GET /orders/<order_id>` → `get_order` → `repo.get`; a missing row returns `status: missing`, otherwise the `Order` dataclass dictionary and an in-memory `read` event are returned.

## Storage

The only durable store is the SQLite database at `Settings.database_path`, defaulting to a relative `orders.sqlite` in the process working directory. The `orders` table has a primary key `order_id`, required `customer`, and required integer `total_cents`. `save` relies on SQLite errors for duplicate IDs and other failures; it does not implement retries, transactions spanning multiple operations, or durability configuration beyond SQLite defaults. Events returned by `order_event` are transient response data, not rows in an audit table.

## Risks and extension points

- **Readonly gap:** `MINISVC_READONLY=1` currently changes configuration state only; `create_order` can still call `save`, and CLI startup still calls `init_schema`. Enforce the policy at the application/repository write boundary and decide whether schema initialization is allowed.
- **Input validation:** missing payload keys raise `KeyError`; malformed `total_cents` raises `ValueError`; no checks enforce non-empty strings, non-negative totals, bounds, or unknown-field policy. Add an explicit request validation layer and map failures to stable HTTP errors.
- **Failure handling:** `save` is one attempt. Duplicate IDs and SQLite operational errors propagate through the handler. Add narrowly scoped retry policy only for retryable database errors, with idempotency handling for repeated creates.
- **Audit semantics:** `order_event` is response shaping, not an audit trail. If auditability is required, define an append-only schema/sink, atomicity with the order write, and retention/access controls.
- **Runtime environment:** relative database paths depend on the current working directory, and `main` does not start an HTTP adapter. Deployment integration must supply an app/server lifecycle and an explicit database path.

The clean extension seams are `Settings` for runtime configuration, `OrderRepository` for persistence, `register_routes` for framework binding, and the handler functions for validation and application policy.

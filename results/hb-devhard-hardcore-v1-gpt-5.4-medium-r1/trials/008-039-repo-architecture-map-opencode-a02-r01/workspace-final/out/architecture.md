# minisvc Architecture Summary

## Overview

`minisvc` is a small Python service skeleton centered on one domain object: `Order`. The codebase contains a CLI bootstrap path, route registration helpers for an HTTP adapter, simple request handlers, and a SQLite-backed repository.

The active runtime code is concentrated in:

- `minisvc/cli.py`
- `minisvc/config.py`
- `minisvc/models.py`
- `minisvc/api/routes.py`
- `minisvc/api/handlers.py`
- `minisvc/audit.py`
- `minisvc/storage/repo.py`

The package marker files `minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are not business-logic modules.

## Modules

| Module | Purpose |
| --- | --- |
| `minisvc.cli` | CLI bootstrap. Loads settings, creates `OrderRepository`, initializes schema, and prints readiness. |
| `minisvc.config` | Defines frozen `Settings` and loads `MINISVC_DB` plus `MINISVC_READONLY` from the environment. |
| `minisvc.models` | Defines the `Order` dataclass shared across layers. |
| `minisvc.api.routes` | Registers HTTP routes by mapping framework callbacks to handler functions. |
| `minisvc.api.handlers` | Converts payloads into `Order` instances, calls the repository, and shapes HTTP responses. |
| `minisvc.audit` | Builds order event dictionaries for responses. No persistence. |
| `minisvc.storage.repo` | Encapsulates SQLite schema creation, inserts, and reads for orders. |

## Entry Points

- `minisvc.cli:main`
  `pyproject.toml` exposes this as the `minisvc` console script.
- `minisvc.api.routes:register_routes`
  This is the HTTP integration point. A caller must pass an app object with `post` and `get` registration methods plus a repository instance.

## Data Flow

### CLI startup flow

1. The console script resolves to `minisvc.cli:main`.
2. `main` loads settings from `os.environ` via `load_settings`.
3. `main` instantiates `OrderRepository(settings.database_path)`.
4. `main` calls `repo.init_schema()` to ensure the `orders` table exists.
5. `main` prints a ready message and exits.

This path prepares storage but does not run an HTTP server.

### HTTP create-order flow

1. Some outer application calls `register_routes(app, repo)`.
2. `register_routes` binds POST `/orders` to `create_order(payload, repo)`.
3. `create_order` reads `order_id`, `customer`, and `total_cents` directly from the request payload.
4. It constructs an `Order` dataclass and calls `repo.save(order)`.
5. `repo.save` opens a SQLite connection and inserts into the `orders` table.
6. `create_order` builds an event dict with `order_event(order, "created")`.
7. The handler returns `{"status": "created", "order_id": ..., "event": ...}`.

### HTTP read-order flow

1. `register_routes` binds GET `/orders/<order_id>` to `get_order(order_id, repo)`.
2. `get_order` calls `repo.get(order_id)`.
3. `repo.get` queries SQLite and either returns `Order(...)` or `None`.
4. The handler returns either a `missing` response or an `ok` response with `order.__dict__` and a computed read event.

## Storage

- Storage backend: local SQLite database via `sqlite3`.
- Configured by: `MINISVC_DB`, defaulting to `orders.sqlite`.
- Schema owner: `OrderRepository.init_schema()`.
- Tables created by code: `orders` only.

Important limitation: there is no audit table, no migration layer, and no explicit durability tuning beyond SQLite's defaults.

## Risks And Extension Points

### Risks

- `MINISVC_READONLY` is parsed but never enforced. Write paths still call `repo.save`.
- `create_order` has no retry behavior despite the README design note.
- Audit behavior is response-only. `order_event` returns a dict and does not persist anything.
- Request validation is thin. Missing fields, bad integer conversion, or duplicate keys will raise exceptions.
- The CLI initializes schema, but the HTTP path shown here has no guaranteed bootstrap step unless the embedding app calls it.

### Extension points

- Add a service layer between handlers and storage if business rules grow.
- Replace route lambdas with explicit adapter functions if framework-specific request/response handling is needed.
- Introduce durable audit persistence in `storage` or a separate repository.
- Enforce readonly behavior either in handlers, a service layer, or the repository.
- Add structured validation around `create_order` inputs before constructing `Order`.

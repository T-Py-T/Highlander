# minisvc architecture

## What is active runtime code
- `minisvc/cli.py`: real startup path. `minisvc.cli:main` is the console-script entry point declared in `pyproject.toml`.
- `minisvc/config.py`: real configuration loader for `MINISVC_DB` and `MINISVC_READONLY`.
- `minisvc/storage/repo.py`: real persistence layer. Owns schema creation plus order insert/read queries.
- `minisvc/api/handlers.py`: real use-case logic for create/read order flows.
- `minisvc/api/routes.py`: real integration hook that registers HTTP routes onto an external app object.
- `minisvc/audit.py`: real helper that builds response-local audit event payloads.
- `minisvc/models.py`: real shared data model.

## What is not business logic
- `minisvc/__init__.py`, `minisvc/api/__init__.py`, `minisvc/storage/__init__.py`: package markers only. No runtime behavior.
- `pyproject.toml`: packaging metadata plus console-script declaration.
- `README.md`: documentation only; some claims do not match code.

## Module map
| Module | Purpose | Notes |
| --- | --- | --- |
| `minisvc.cli` | Bootstrap the service runtime. | Loads settings, creates repository, initializes SQLite schema, prints readiness. |
| `minisvc.config` | Convert environment variables into `Settings`. | Supports `MINISVC_DB`; parses `MINISVC_READONLY=1` to `readonly=True`. |
| `minisvc.models` | Define `Order`. | `dataclass` used across API and storage layers. |
| `minisvc.storage.repo` | Persist and fetch orders in SQLite. | One table: `orders(order_id, customer, total_cents)`. |
| `minisvc.api.handlers` | Implement create/read order use-cases. | No HTTP framework dependency beyond input/output dicts. |
| `minisvc.api.routes` | Adapt handlers to an app/router object. | Expects `app.post()` and `app.get()` methods. |
| `minisvc.audit` | Build audit event dicts. | Pure helper; no storage side effects. |

## Entry points
- `minisvc.cli:main`: executable console entry point.
- `minisvc.api.routes:register_routes`: API integration entry point for wiring routes.
- Routed handler targets:
  - `minisvc.api.handlers:create_order`
  - `minisvc.api.handlers:get_order`

## Data flow
### CLI startup
1. `minisvc.cli:main` reads `os.environ`.
2. `minisvc.config:load_settings` builds `Settings(database_path, readonly)`.
3. `main` constructs `OrderRepository(settings.database_path)`.
4. `OrderRepository.init_schema()` creates the `orders` table if needed.
5. `main` prints `minisvc ready at ...` and exits `0`.

### HTTP create-order flow
1. Integrator calls `minisvc.api.routes:register_routes(app, repo)`.
2. `register_routes` binds `POST /orders` to `create_order(payload, repo)`.
3. `create_order` pulls `order_id`, `customer`, and `total_cents` from the payload.
4. It creates `Order(...)`, coercing `total_cents` with `int()`.
5. It calls `OrderRepository.save(order)`.
6. `save` opens SQLite and inserts the row.
7. `create_order` returns `{status, order_id, event}` where `event` comes from `minisvc.audit:order_event`.

### HTTP read flow
1. `register_routes` binds `GET /orders/<order_id>` to `get_order(order_id, repo)`.
2. `get_order` calls `repo.get(order_id)`.
3. Missing row -> `{status: "missing", order_id}`.
4. Present row -> `{status: "ok", order: order.__dict__, event: order_event(..., "read")}`.

## Storage
- Backend: SQLite via the standard-library `sqlite3` module.
- File location: `Settings.database_path`, default `orders.sqlite` in the current working directory.
- Schema: exactly one durable table, `orders`.
- No repository abstraction beyond `OrderRepository`; each method opens a fresh connection.
- No audit table. Audit data exists only in returned response dicts.

## Risks and extension points
### Risks
- Read-only mode is parsed but never enforced. Any caller with a repository can still write through `create_order`.
- `create_order` has no validation guardrails beyond `int(total_cents)`. Missing keys, non-integer totals, duplicate IDs, and SQLite write failures propagate as exceptions.
- No retry behavior around `repo.save()`. Transient SQLite failures fail the request immediately.
- Audit events are not durable. Process restarts lose all audit history because only the `orders` table exists.
- Route wiring depends on an external app shape but provides no adapter contract or framework-specific integration tests.

### Extension points
- Add validation and error translation in `minisvc.api.handlers` before persistence.
- Enforce `Settings.readonly` either in handlers or repository methods.
- Add durable audit persistence beside `OrderRepository` or inside a widened repository transaction.
- Replace the lambda wrappers in `minisvc.api.routes` with framework-native handlers once an actual web stack is chosen.

Outcome: I inspected only `/workspace/in/repo`, made no changes, and used no internet. The code shows a small SQLite-backed order service with clear doc/code gaps around readonly enforcement, retry behavior, and audit persistence. The main risks are weak write controls, non-durable audit events, minimal runtime config, and unvalidated API payloads.

## Scope

This branch covers risk and onboarding synthesis inputs only:

- Storage durability
- Audit behavior
- Config/runtime environment
- API validation
- Onboarding guidance grounded in observed modules, flows, and doc/code gaps

## Contract amendments received

No mid-run steering amendments were received after launch.

## Findings

### Repository/module map inputs relevant to onboarding

Package marker files:

- `/workspace/in/repo/minisvc/__init__.py` only defines `__all__ = ["config", "models"]`; it is package metadata, not active business logic.
- `/workspace/in/repo/minisvc/api/__init__.py` is empty.
- `/workspace/in/repo/minisvc/storage/__init__.py` is empty.

Active modules:

- `/workspace/in/repo/minisvc/cli.py`
  - Entry point: `main(argv=None)`.
  - Loads settings from `os.environ`.
  - Instantiates `OrderRepository`.
  - Calls `repo.init_schema()`.
- `/workspace/in/repo/minisvc/config.py`
  - Defines `Settings`.
  - Defines `load_settings(env)`.
  - Reads `MINISVC_DB` and `MINISVC_READONLY`.
- `/workspace/in/repo/minisvc/api/routes.py`
  - Entry point: `register_routes(app, repo)`.
  - Registers POST `/orders` and GET `/orders/<order_id>`.
- `/workspace/in/repo/minisvc/api/handlers.py`
  - Defines `create_order(payload, repo)`.
  - Defines `get_order(order_id, repo)`.
  - Creates `Order`, calls repository methods, and returns audit event dicts.
- `/workspace/in/repo/minisvc/storage/repo.py`
  - Defines `OrderRepository`.
  - Persists orders to SQLite table `orders`.
  - Reads orders from SQLite.
- `/workspace/in/repo/minisvc/audit.py`
  - Defines `order_event(order, action)`.
  - Builds an in-memory event dict only.
- `/workspace/in/repo/minisvc/models.py`
  - Defines dataclass `Order`.

Canonical entry points:

- CLI: `minisvc.cli:main`, declared in `/workspace/in/repo/pyproject.toml`.
- HTTP route registration: `minisvc.api.routes:register_routes`.

### Runtime flows

CLI startup flow:

1. `minisvc.cli:main` receives optional `argv`, but does not use it.
2. It calls `load_settings(os.environ)`.
3. `load_settings` reads:
   - `MINISVC_DB`, defaulting to `orders.sqlite`.
   - `MINISVC_READONLY`, true only when value is `"1"`.
4. `main` creates `OrderRepository(settings.database_path)`.
5. `main` calls `repo.init_schema()`.
6. `init_schema` connects to SQLite and creates table `orders` if missing.
7. `main` prints `minisvc ready at {settings.database_path}` and returns `0`.

HTTP create-order flow:

1. `register_routes(app, repo)` binds POST `/orders` to `lambda payload: create_order(payload, repo)`.
2. `create_order(payload, repo)` reads `payload["order_id"]`, `payload["customer"]`, and `payload["total_cents"]`.
3. It casts `payload["total_cents"]` with `int(...)`.
4. It constructs `Order`.
5. It calls `repo.save(order)`.
6. `repo.save` opens a SQLite connection and inserts into `orders`.
7. `create_order` returns `{"status": "created", "order_id": ..., "event": order_event(order, "created")}`.
8. `order_event` returns an in-memory dict; no audit table or file write occurs.

## Evidence

Observed files and commands:

- File inventory came from `find /workspace/in/repo -maxdepth 4 -type f | sort`.
- Import/function/config scan came from `grep -R "MINISVC\\|sqlite\\|execute\\|def \\|class \\|import \\|from " -n /workspace/in/repo | sort`.
- Source lines were read directly from:
  - `/workspace/in/repo/README.md`
  - `/workspace/in/repo/pyproject.toml`
  - `/workspace/in/repo/minisvc/cli.py`
  - `/workspace/in/repo/minisvc/config.py`
  - `/workspace/in/repo/minisvc/api/routes.py`
  - `/workspace/in/repo/minisvc/api/handlers.py`
  - `/workspace/in/repo/minisvc/audit.py`
  - `/workspace/in/repo/minisvc/models.py`
  - `/workspace/in/repo/minisvc/storage/repo.py`
  - package `__init__.py` files

Key concrete evidence:

- README says older design notes claimed:
  - `MINISVC_READONLY=1` blocks all write paths.
  - `create_order` retries failed SQLite writes twice.
  - Audit events are stored in a durable audit table.
  - Code is authoritative when docs disagree.
- `config.load_settings` parses `readonly`, but no observed caller enforces it.
- `cli.main` creates the repository using only `settings.database_path`; it does not pass `settings.readonly`.
- `OrderRepository.save` performs one SQLite insert and has no retry loop.
- `OrderRepository.init_schema` creates only `orders`; no audit table exists.
- `audit.order_event` returns a dict and performs no persistence.
- `api.handlers.create_order` indexes payload keys directly and casts `total_cents` with `int(...)`; it has no explicit validation or structured error handling.

## Conflicts or uncertainty

### Doc/code discrepancies for synthesis

```csv
topic,documentation_claim,actual_code,evidence,risk
readonly enforcement,"MINISVC_READONLY=1 blocks all write paths","readonly is parsed in config but not enforced by cli, handlers, or repository","README.md design note; config.load_settings; cli.main; storage.repo.OrderRepository.save","Operators may believe writes are disabled when they are not"
retry behavior,"create_order retries failed SQLite writes twice before returning an error response","create_order calls repo.save once; repo.save performs one insert with no retry handling","README.md design note; api.handlers.create_order; storage.repo.OrderRepository.save","Transient SQLite errors surface directly or break request handling"
audit persistence,"Audit events are stored in a durable audit table","audit.order_event returns a dict; init_schema creates only orders table","README.md design note; audit.order_event; storage.repo.OrderRepository.init_schema","Audit trail is not durable and is lost unless caller stores response elsewhere"
```

### Uncertainty

- No app framework implementation is present, so exact HTTP server behavior and error serialization cannot be verified.
- No tests are present in the observed file list.
- SQLite transaction durability settings such as WAL, synchronous mode, timeouts, migrations, or backups are not configured in observed code.
- The code may rely on an external caller to handle audit persistence or validation, but no such caller exists in `/workspace/in/repo`.

## Recommendations

### Draft `risk_register.csv`

```csv
risk_id,area,risk,impact,evidence,likelihood,severity,mitigation
R-001,storage durability,"SQLite writes use default connection settings with no retry, timeout, migration strategy, or backup policy","Order writes may fail under lock contention or be hard to recover after local disk loss","storage.repo.OrderRepository.save opens sqlite3.connect and executes one insert; init_schema creates only orders table","medium","high","Add explicit SQLite timeout/config, retry policy where desired, migration/versioning, and documented backup/restore expectations"
R-002,audit behavior,"Audit events are response payloads only, not durable records","Created/read events can be lost and cannot support compliance or later investigation","audit.order_event returns dict; storage.repo.init_schema creates no audit table","high","high","Persist audit events in a table or external sink, add tests, and update README to match behavior"
R-003,config/runtime environment,"MINISVC_READONLY is parsed but not enforced","Operators may set readonly mode and still allow schema creation and order inserts","config.load_settings returns readonly; cli.main ignores settings.readonly except database_path; repo.save has no readonly check","high","high","Thread Settings into write paths or repository, block init_schema/save when readonly, and add tests"
R-004,config/runtime environment,"Default database path is relative orders.sqlite","Runtime data location may vary by working directory, causing data split or loss in deployments","config.load_settings defaults MINISVC_DB to orders.sqlite","medium","medium","Require explicit MINISVC_DB in production or resolve to a documented data directory"
R-005,API validation,"create_order directly indexes payload keys and casts total_cents without validation","Bad requests can raise KeyError, ValueError, or TypeError instead of returning clear client errors","api.handlers.create_order uses payload['order_id'], payload['customer'], int(payload['total_cents'])","high","medium","Add request schema validation, type/range checks, and stable error responses"
R-006,API validation,"Duplicate order IDs are not handled at handler level","SQLite primary key conflicts may raise raw exceptions","orders table defines order_id primary key; repo.save uses insert; create_order has no exception handling","medium","medium","Catch integrity errors and return conflict response"
```

### Draft `onboarding_plan.md`

```markdown
# Onboarding plan for minisvc

## Start with the active entry points

1. Read `pyproject.toml` to confirm the CLI command:
   - `minisvc = "minisvc.cli:main"`
2. Read `minisvc/cli.py`.
   - `main` loads environment settings, creates `OrderRepository`, initializes the schema, prints readiness, and returns `0`.
3. Read `minisvc/api/routes.py`.
   - `register_routes(app, repo)` registers POST `/orders` and GET `/orders/<order_id>`.

## Understand package marker files

The following files are package markers, not business logic:

- `minisvc/__init__.py`
- `minisvc/api/__init__.py`
- `minisvc/storage/__init__.py`

Do not infer behavior from these files beyond package layout.

## Trace the create-order path

1. `register_routes` maps POST `/orders` to `create_order(payload, repo)`.
2. `create_order` builds an `Order` from `order_id`, `customer`, and `total_cents`.
3. `create_order` calls `repo.save(order)`.
4. `OrderRepository.save` inserts the order into SQLite table `orders`.
5. `create_order` returns a response with an audit event dict from `order_event`.

Important caveat: the audit event is not persisted by current code.

## Trace the read-order path

1. `register_routes` maps GET `/orders/<order_id>` to `get_order(order_id, repo)`.
2. `get_order` calls `repo.get(order_id)`.
3. `OrderRepository.get` selects from SQLite.
4. Missing orders return `{"status": "missing", "order_id": order_id}`.
5. Found orders return status `ok`, the order dict, and an audit event dict.

Important caveat: read audit events are also not persisted.

## Learn the config model

`minisvc/config.py` defines:

- `MINISVC_DB`, default `orders.sqlite`
- `MINISVC_READONLY`, true only when value is `"1"`

Current code parses readonly but does not enforce it. Treat README readonly claims as stale until code changes.

## Review doc/code gaps before making changes

The README labels its design notes as older and says code is authoritative. Known gaps:

- Readonly enforcement is documented but not implemented.
- Retry-on-write is documented but not implemented.
- Durable audit table is documented but not implemented.

## First safe improvement areas

1. Add tests for current behavior before changing it:
   - CLI initializes schema.
   - `create_order` saves an order.
   - invalid payloads currently raise exceptions.
   - readonly currently does not block writes.
2. Decide expected behavior for readonly:
   - Should CLI schema creation be blocked?
   - Should POST `/orders` be blocked?
   - Should GET `/orders/<order_id>` remain allowed?
3. Decide expected audit persistence:
   - SQLite audit table, file sink, or external adapter.
4. Decide expected validation errors:
   - Missing fields.
   - Non-integer `total_cents`.
   - Negative totals.
   - Duplicate `order_id`.

## Risk areas for new contributors

- SQLite is used directly with default settings.
- There is no migration layer.
- There is no retry or error response layer.
- Runtime config is environment-only.
- The HTTP adapter shape is minimal and framework behavior is not present in this repository.
```
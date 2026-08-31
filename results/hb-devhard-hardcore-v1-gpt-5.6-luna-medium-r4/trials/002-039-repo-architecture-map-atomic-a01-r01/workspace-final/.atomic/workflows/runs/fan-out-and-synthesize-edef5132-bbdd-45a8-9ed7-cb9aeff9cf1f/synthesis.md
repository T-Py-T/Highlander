Outcome: all three completed branches in the manifest are accounted for. The synthesized architecture is a small Python SQLite-backed order service with two confirmed canonical entry points: `minisvc.cli:main` and `minisvc.api.routes:register_routes`. The code does not implement the README’s older notes for readonly write blocking, SQLite write retries, or durable audit persistence.

## Executive synthesis

I audited each claim below against tool-read artifacts from this session:

- Manifest: `/workspace/.atomic/workflows/runs/fan-out-and-synthesize-edef5132-bbdd-45a8-9ed7-cb9aeff9cf1f/manifest.json`
- Branch 01, Code architecture and runtime flows: `/workspace/.atomic/workflows/runs/fan-out-and-synthesize-edef5132-bbdd-45a8-9ed7-cb9aeff9cf1f/branch-01-code-architecture-and-runtime-flows.md`
- Branch 02, Docs versus code discrepancies: `/workspace/.atomic/workflows/runs/fan-out-and-synthesize-edef5132-bbdd-45a8-9ed7-cb9aeff9cf1f/branch-02-docs-versus-code-discrepancies.md`
- Branch 03, Risks and onboarding synthesis inputs: `/workspace/.atomic/workflows/runs/fan-out-and-synthesize-edef5132-bbdd-45a8-9ed7-cb9aeff9cf1f/branch-03-risks-and-onboarding-synthesis-inputs.md`

I did not inspect `/workspace/in/repo` directly in this synthesis stage, so line-level code facts are carried from the branch artifacts.

## Contract amendments received

Inherited launch contract: “Inspect only /workspace/in/repo; do not modify it and do not use internet.”

Branch reports state no further objective-relevant steering amendments were received:
- Branch 01: “None beyond the launch contract.”
- Branch 02: “None.”
- Branch 03: “No mid-run steering amendments were received after launch.”

## Consolidated findings

### `module_map.json`

```json
{
  "entry_points": [
    {
      "name": "minisvc.cli:main",
      "type": "console_script",
      "declared_in": "pyproject.toml",
      "evidence": [
        "Branch 01 cites pyproject.toml:6-7",
        "Branch 03 confirms canonical CLI entry point"
      ]
    },
    {
      "name": "minisvc.api.routes:register_routes",
      "type": "http_route_registration",
      "declared_in": "minisvc/api/routes.py",
      "evidence": [
        "Branch 01 cites minisvc/api/routes.py:4",
        "Branch 03 confirms HTTP route registration entry point"
      ]
    }
  ],
  "modules": [
    {
      "module": "minisvc.__init__",
      "file": "minisvc/__init__.py",
      "role": "package marker/export list",
      "active_business_logic": false,
      "key_symbols": ["__all__"],
      "evidence": "Branch 01 says line 1 only sets __all__; Branch 03 says it is package metadata."
    },
    {
      "module": "minisvc.api.__init__",
      "file": "minisvc/api/__init__.py",
      "role": "package marker",
      "active_business_logic": false,
      "key_symbols": [],
      "evidence": "Branches 01 and 03 report it is empty."
    },
    {
      "module": "minisvc.storage.__init__",
      "file": "minisvc/storage/__init__.py",
      "role": "package marker",
      "active_business_logic": false,
      "key_symbols": [],
      "evidence": "Branches 01 and 03 report it is empty."
    },
    {
      "module": "minisvc.cli",
      "file": "minisvc/cli.py",
      "role": "CLI startup/bootstrap",
      "active_business_logic": true,
      "key_functions": ["main(argv=None)"],
      "dependency_edges": [
        {"kind": "imports", "target": "os"},
        {"kind": "imports", "target": "minisvc.config.load_settings"},
        {"kind": "imports", "target": "minisvc.storage.repo.OrderRepository"},
        {"kind": "reads_config", "target": "os.environ via load_settings"},
        {"kind": "instantiates", "target": "OrderRepository(settings.database_path)"},
        {"kind": "calls", "target": "repo.init_schema()"}
      ],
      "evidence": "Branch 01 cites cli.py:1,3-4,7-12; Branch 03 confirms flow."
    },
    {
      "module": "minisvc.config",
      "file": "minisvc/config.py",
      "role": "environment-backed settings",
      "active_business_logic": true,
      "key_classes": ["Settings"],
      "key_functions": ["load_settings(env)"],
      "dependency_edges": [
        {"kind": "imports", "target": "dataclasses.dataclass"},
        {"kind": "reads_config", "target": "MINISVC_DB"},
        {"kind": "reads_config", "target": "MINISVC_READONLY"}
      ],
      "evidence": "Branch 01 cites config.py:1,10-13; Branch 03 confirms env keys and defaults."
    },
    {
      "module": "minisvc.models",
      "file": "minisvc/models.py",
      "role": "domain data model",
      "active_business_logic": true,
      "key_classes": ["Order"],
      "dependency_edges": [
        {"kind": "imports", "target": "dataclasses.dataclass"}
      ],
      "evidence": "Branches 01 and 03 identify Order dataclass."
    },
    {
      "module": "minisvc.api.routes",
      "file": "minisvc/api/routes.py",
      "role": "HTTP route registration",
      "active_business_logic": true,
      "key_functions": ["register_routes(app, repo)"],
      "dependency_edges": [
        {"kind": "imports", "target": "minisvc.api.handlers.create_order"},
        {"kind": "imports", "target": "minisvc.api.handlers.get_order"},
        {"kind": "calls", "target": "app.post('/orders', ...)"},
        {"kind": "calls", "target": "app.get('/orders/<order_id>', ...)"},
        {"kind": "calls", "target": "create_order(payload, repo)"},
        {"kind": "calls", "target": "get_order(order_id, repo)"}
      ],
      "evidence": "Branch 01 cites routes.py:1,4-6; Branch 03 confirms registered routes."
    },
    {
      "module": "minisvc.api.handlers",
      "file": "minisvc/api/handlers.py",
      "role": "HTTP request handlers/order use cases",
      "active_business_logic": true,
      "key_functions": ["create_order(payload, repo)", "get_order(order_id, repo)"],
      "dependency_edges": [
        {"kind": "imports", "target": "minisvc.audit.order_event"},
        {"kind": "imports", "target": "minisvc.models.Order"},
        {"kind": "imports", "target": "minisvc.storage.repo.OrderRepository"},
        {"kind": "instantiates", "target": "Order(...)"},
        {"kind": "calls", "target": "repo.save(order)"},
        {"kind": "calls", "target": "repo.get(order_id)"},
        {"kind": "calls", "target": "order_event(order, 'created')"},
        {"kind": "calls", "target": "order_event(order, 'read')"}
      ],
      "evidence": "Branch 01 cites handlers.py:1-3,6-20; Branch 03 confirms create/read flows."
    },
    {
      "module": "minisvc.audit",
      "file": "minisvc/audit.py",
      "role": "in-memory audit event builder",
      "active_business_logic": true,
      "key_functions": ["order_event(order, action)"],
      "dependency_edges": [
        {"kind": "imports", "target": "minisvc.models.Order"}
      ],
      "evidence": "Branch 01 cites audit.py:1,4-10; Branch 03 says no persistence occurs."
    },
    {
      "module": "minisvc.storage.repo",
      "file": "minisvc/storage/repo.py",
      "role": "SQLite repository",
      "active_business_logic": true,
      "key_classes": ["OrderRepository"],
      "key_functions": ["__init__", "init_schema", "save", "get"],
      "dependency_edges": [
        {"kind": "imports", "target": "sqlite3"},
        {"kind": "imports", "target": "pathlib.Path"},
        {"kind": "imports", "target": "minisvc.models.Order"},
        {"kind": "instantiates", "target": "Path(database_path)"},
        {"kind": "persists_to", "target": "SQLite orders table"},
        {"kind": "calls", "target": "sqlite3.connect(self.database_path)"},
        {"kind": "calls", "target": "Order(*row)"}
      ],
      "evidence": "Branch 01 cites repo.py:1-4,8-30; Branch 03 confirms order persistence."
    }
  ]
}
```

### `architecture.md`

`/workspace/in/repo` contains a compact Python package named `minisvc`.

The CLI starts at `minisvc.cli:main`, declared in `pyproject.toml`. `main(argv=None)` reads settings through `load_settings(os.environ)`, creates `OrderRepository(settings.database_path)`, runs `repo.init_schema()`, prints a ready message, and returns `0`. `argv` is accepted but not used. Evidence comes from Branch 01, which cites `pyproject.toml:6-7`, `cli.py:7-12`, and `config.py:10-13`, and Branch 03, which confirms the same startup flow.

The HTTP route adapter starts at `minisvc.api.routes:register_routes`. It registers `POST /orders` to `create_order(payload, repo)` and `GET /orders/<order_id>` to `get_order(order_id, repo)`. The concrete HTTP framework is not present in the repository; the function assumes an `app` object with `.post` and `.get`. Evidence comes from Branch 01, which cites `routes.py:4-6`, and Branch 03, which preserves the missing-framework uncertainty.

The create-order flow is direct. `create_order(payload, repo)` reads `payload["order_id"]`, `payload["customer"]`, and `payload["total_cents"]`, casts `total_cents` with `int(...)`, constructs an `Order`, calls `repo.save(order)`, and returns a response with status `created`, the order ID, and an audit event dict. `OrderRepository.save` opens SQLite and inserts into the `orders` table. `audit.order_event` returns an in-memory dict. Evidence comes from Branch 01, which cites `handlers.py:6-13`, `repo.py:17-22`, and `audit.py:4-10`, and Branch 03, which confirms no audit table or file write occurs.

The read-order flow is also direct. `get_order(order_id, repo)` calls `repo.get(order_id)`. Missing orders return `{"status": "missing", "order_id": order_id}`. Found orders return status `ok`, an order dict, and an audit event dict. Evidence comes from Branch 01 dependency edges for `repo.get` and `order_event(order, "read")`, and Branch 03’s onboarding flow.

Package marker files must not be treated as business logic:
- `minisvc/__init__.py` only sets `__all__`.
- `minisvc/api/__init__.py` is empty.
- `minisvc/storage/__init__.py` is empty.

### `doc_code_discrepancies.csv`

```csv
topic,doc_claim,code_observed,discrepancy,evidence
readonly enforcement,"README says MINISVC_READONLY=1 blocks all write paths.","load_settings parses MINISVC_READONLY into Settings.readonly, but cli.main does not pass or enforce readonly; create_order calls repo.save(order) unconditionally; init_schema and save write to SQLite with no readonly guard.","Documented readonly blocking is not enforced.","Branch 02 cites README.md:5-8, config.py:4-14, cli.py:7-11, api/handlers.py:6-13, storage/repo.py:11-22; Branch 01 and Branch 03 agree."
retry behavior,"README says create_order retries failed SQLite writes twice before returning an error response.","create_order calls repo.save(order) once; OrderRepository.save performs one insert; no loop, retry helper, try/except, or error mapping was found.","Documented retry behavior is absent.","Branch 02 cites README.md:5-8, api/handlers.py:6-13, storage/repo.py:17-22; Branch 01 and Branch 03 agree."
audit persistence,"README says audit events are stored in a durable audit table.","order_event only builds and returns a dict; create_order and get_order include the dict in responses; init_schema creates only an orders table; no audit insert exists.","Documented durable audit persistence is absent.","Branch 02 cites README.md:5-8, audit.py:4-10, api/handlers.py:12-20, storage/repo.py:11-22; Branch 01 and Branch 03 agree."
```

### `risk_register.csv`

```csv
risk_id,area,risk,impact,evidence,likelihood,severity,mitigation
R-001,storage durability,"SQLite writes use default connection settings with no retry, timeout, migration strategy, or backup policy.","Order writes may fail under lock contention or be hard to recover after local disk loss.","Branch 03: OrderRepository.save opens sqlite3.connect and executes one insert; init_schema creates only orders table.",medium,high,"Add explicit SQLite timeout/config, retry policy if desired, migration/versioning, and backup/restore guidance."
R-002,audit behavior,"Audit events are response payloads only, not durable records.","Created/read events can be lost and cannot support later investigation unless callers store responses elsewhere.","Branch 01: audit.py:4-10 returns dict; Branch 03: init_schema creates no audit table.",high,high,"Persist audit events in a table or external sink, add tests, and update README."
R-003,config/runtime environment,"MINISVC_READONLY is parsed but not enforced.","Operators may set readonly mode and still allow schema creation and order inserts.","Branch 02: config parses readonly; cli.main, handlers, and repo do not enforce it.",high,high,"Thread Settings into write paths or repository, block init_schema/save as intended, and add tests."
R-004,config/runtime environment,"Default database path is relative orders.sqlite.","Runtime data location may vary by working directory, causing split or lost data in deployments.","Branch 03: config.load_settings defaults MINISVC_DB to orders.sqlite.",medium,medium,"Require explicit MINISVC_DB in production or resolve to a fixed data directory."
R-005,API validation,"create_order directly indexes payload keys and casts total_cents without validation.","Bad requests can raise KeyError, ValueError, or TypeError instead of stable client errors.","Branch 03: create_order uses payload['order_id'], payload['customer'], int(payload['total_cents']).",high,medium,"Add request schema validation, type/range checks, and stable error responses."
R-006,API validation,"Duplicate order IDs are not handled at handler level.","SQLite primary key conflicts may raise raw exceptions.","Branch 03: orders table uses order_id primary key; repo.save inserts; create_order has no exception handling.",medium,medium,"Catch integrity errors and return a conflict response."
```

### `onboarding_plan.md`

```markdown
# Onboarding plan for minisvc

## Start with entry points

1. Read `pyproject.toml` to confirm `minisvc = "minisvc.cli:main"`.
2. Read `minisvc/cli.py`.
   - `main` loads env settings, creates `OrderRepository`, initializes schema, prints readiness, and returns `0`.
3. Read `minisvc/api/routes.py`.
   - `register_routes(app, repo)` registers POST `/orders` and GET `/orders/<order_id>`.

## Know package marker files

These files are package markers, not active business logic:

- `minisvc/__init__.py`
- `minisvc/api/__init__.py`
- `minisvc/storage/__init__.py`

## Trace create-order

1. `register_routes` maps POST `/orders` to `create_order(payload, repo)`.
2. `create_order` builds an `Order` from `order_id`, `customer`, and `total_cents`.
3. `create_order` calls `repo.save(order)`.
4. `OrderRepository.save` inserts into SQLite table `orders`.
5. `create_order` returns an audit event dict from `order_event`.

Caveat: audit events are not persisted by current code.

## Trace read-order

1. `register_routes` maps GET `/orders/<order_id>` to `get_order(order_id, repo)`.
2. `get_order` calls `repo.get(order_id)`.
3. `OrderRepository.get` selects from SQLite.
4. Missing orders return status `missing`.
5. Found orders return status `ok`, an order dict, and an audit event dict.

Caveat: read audit events are not persisted.

## Learn config

`minisvc/config.py` defines:

- `MINISVC_DB`, default `orders.sqlite`
- `MINISVC_READONLY`, true only when value is `"1"`

Current code parses readonly but does not enforce it.

## Review doc/code gaps

The README says older design notes claimed readonly blocking, retry-on-write, and durable audit tables. The README also says code is authoritative when docs and implementation disagree.

Known gaps:

- Readonly enforcement is documented but not implemented.
- Retry-on-write is documented but not implemented.
- Durable audit persistence is documented but not implemented.

## First safe work

1. Add tests for current behavior:
   - CLI initializes schema.
   - `create_order` saves an order.
   - invalid payloads currently raise exceptions.
   - readonly currently does not block writes.
2. Decide intended readonly behavior.
3. Decide intended audit persistence.
4. Decide intended validation and error response behavior.
5. Decide how to handle duplicate `order_id`.

## Risk areas

- SQLite is used directly with default settings.
- There is no migration layer.
- There is no retry or error response layer.
- Runtime config is environment-only.
- The HTTP adapter is minimal, and no concrete HTTP framework exists in this repository.
```

## Conflicts and resolutions

| Topic | Branch evidence | Resolution |
|---|---|---|
| README design notes vs code | Branches 01, 02, and 03 all report README notes claim readonly blocking, retries, and durable audit persistence, while code lacks them. Branch 02 adds that README says code is authoritative. | Treat the README design notes as stale, not implemented behavior. Preserve them in `doc_code_discrepancies.csv`. |
| Readonly setting | Branches 01 and 03 say `MINISVC_READONLY` is parsed. Branches 01, 02, and 03 say no write path enforces it. | Record a `reads_config` edge for `MINISVC_READONLY`, but no enforcement edge. Treat write blocking as absent. |
| Audit behavior | Branches 01 and 03 say `order_event` returns a dict. Branch 02 says no audit table or insert exists. | Treat audit as response-only and non-durable. |
| Retry behavior | Branches 01, 02, and 03 say `repo.save` is called once and no retry loop exists. | Treat retries as absent. |
| HTTP framework | Branch 01 says no framework implementation was found. Branch 03 says exact HTTP server behavior and error serialization cannot be verified. | Preserve as uncertainty. Only document `register_routes(app, repo)` and assumed `.post`/`.get` adapter shape. |
| Tests | Branch 03 says no tests were present in the observed file list. Other branches do not contradict this. | Preserve as a risk/onboarding caveat, not as a full repo guarantee beyond branch evidence. |

## Evidence index

- Manifest confirms three branches and their required scopes: `/workspace/.atomic/workflows/runs/fan-out-and-synthesize-edef5132-bbdd-45a8-9ed7-cb9aeff9cf1f/manifest.json`.
- Branch 01 provides the module map, entry points, dependency edges, CLI flow, create-order flow, package marker distinction, and README comparison evidence: `/workspace/.atomic/workflows/runs/fan-out-and-synthesize-edef5132-bbdd-45a8-9ed7-cb9aeff9cf1f/branch-01-code-architecture-and-runtime-flows.md`.
- Branch 02 provides the discrepancy CSV rows for readonly enforcement, retry behavior, and audit persistence: `/workspace/.atomic/workflows/runs/fan-out-and-synthesize-edef5132-bbdd-45a8-9ed7-cb9aeff9cf1f/branch-02-docs-versus-code-discrepancies.md`.
- Branch 03 provides risk register rows, onboarding guidance, read-order flow, and uncertainty around tests, HTTP framework, SQLite settings, and external callers: `/workspace/.atomic/workflows/runs/fan-out-and-synthesize-edef5132-bbdd-45a8-9ed7-cb9aeff9cf1f/branch-03-risks-and-onboarding-synthesis-inputs.md`.

## Remaining uncertainty

- The synthesis stage did not inspect raw repository files; it relies on the three branch artifacts read in this session.
- No concrete HTTP framework implementation was found by the branches, so server behavior and error serialization remain unverified.
- Runtime flows were not executed by the branches; findings are static-code findings.
- No separate design notes file was found; the README was the only design-note source reported.
- Branch 03 reported no tests in the observed file list.
- External callers could add validation, audit persistence, or error handling outside `/workspace/in/repo`, but no such caller was present in the inspected repository evidence.
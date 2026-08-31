Outcome: `/workspace/in/repo` is a small Python service with a CLI bootstrap, an HTTP route adapter, handlers, config, models, audit event creation, and SQLite order storage. The canonical entry points are confirmed as `minisvc.cli:main` and `minisvc.api.routes:register_routes`. No files were modified and no internet was used.

## Scope

I inspected only `/workspace/in/repo`. This branch covers code architecture and runtime flows for use in `module_map.json` and `architecture.md`.

## Contract amendments received

None beyond the launch contract.

## Findings

### Module map for synthesis

```json
{
  "entry_points": [
    {
      "name": "minisvc.cli:main",
      "type": "console_script",
      "declared_in": "pyproject.toml",
      "evidence": "pyproject.toml:6-7 maps minisvc to minisvc.cli:main"
    },
    {
      "name": "minisvc.api.routes:register_routes",
      "type": "http_route_registration",
      "declared_in": "minisvc/api/routes.py",
      "evidence": "minisvc/api/routes.py:4 defines register_routes(app, repo)"
    }
  ],
  "modules": [
    {
      "module": "minisvc.__init__",
      "file": "minisvc/__init__.py",
      "role": "package marker/export list",
      "active_business_logic": false,
      "key_symbols": ["__all__"],
      "evidence": "minisvc/__init__.py:1 only sets __all__"
    },
    {
      "module": "minisvc.api.__init__",
      "file": "minisvc/api/__init__.py",
      "role": "package marker",
      "active_business_logic": false,
      "key_symbols": [],
      "evidence": "file is empty"
    },
    {
      "module": "minisvc.storage.__init__",
      "file": "minisvc/storage/__init__.py",
      "role": "package marker",
      "active_business_logic": false,
      "key_symbols": [],
      "evidence": "file is empty"
    },
    {
      "module": "minisvc.cli",
      "file": "minisvc/cli.py",
      "role": "CLI startup/bootstrap",
      "active_business_logic": true,
      "key_functions": ["main(argv=None)"],
      "dependencies": [
        {"kind": "imports", "target": "os", "evidence": "cli.py:1"},
        {"kind": "imports", "target": "minisvc.config.load_settings", "evidence": "cli.py:3"},
        {"kind": "imports", "target": "minisvc.storage.repo.OrderRepository", "evidence": "cli.py:4"},
        {"kind": "reads_config", "target": "os.environ via load_settings", "evidence": "cli.py:8"},
        {"kind": "instantiates", "target": "OrderRepository(settings.database_path)", "evidence": "cli.py:9"},
        {"kind": "calls", "target": "repo.init_schema()", "evidence": "cli.py:10"}
      ]
    },
    {
      "module": "minisvc.config",
      "file": "minisvc/config.py",
      "role": "environment-backed settings",
      "active_business_logic": true,
      "key_functions": ["load_settings(env)"],
      "key_classes": ["Settings"],
      "dependencies": [
        {"kind": "imports", "target": "dataclasses.dataclass", "evidence": "config.py:1"},
        {"kind": "reads_config", "target": "MINISVC_DB", "evidence": "config.py:12"},
        {"kind": "reads_config", "target": "MINISVC_READONLY", "evidence": "config.py:13"}
      ]
    },
    {
      "module": "minisvc.models",
      "file": "minisvc/models.py",
      "role": "domain data model",
      "active_business_logic": true,
      "key_classes": ["Order"],
      "dependencies": [
        {"kind": "imports", "target": "dataclasses.dataclass", "evidence": "models.py:1"}
      ]
    },
    {
      "module": "minisvc.api.routes",
      "file": "minisvc/api/routes.py",
      "role": "HTTP route registration",
      "active_business_logic": true,
      "key_functions": ["register_routes(app, repo)"],
      "dependencies": [
        {"kind": "imports", "target": "minisvc.api.handlers.create_order", "evidence": "routes.py:1"},
        {"kind": "imports", "target": "minisvc.api.handlers.get_order", "evidence": "routes.py:1"},
        {"kind": "calls", "target": "app.post('/orders', ...)", "evidence": "routes.py:5"},
        {"kind": "calls", "target": "app.get('/orders/<order_id>', ...)", "evidence": "routes.py:6"},
        {"kind": "calls", "target": "create_order(payload, repo)", "evidence": "routes.py:5"},
        {"kind": "calls", "target": "get_order(order_id, repo)", "evidence": "routes.py:6"}
      ]
    },
    {
      "module": "minisvc.api.handlers",
      "file": "minisvc/api/handlers.py",
      "role": "HTTP request handlers/order use cases",
      "active_business_logic": true,
      "key_functions": ["create_order(payload, repo)", "get_order(order_id, repo)"],
      "dependencies": [
        {"kind": "imports", "target": "minisvc.audit.order_event", "evidence": "handlers.py:1"},
        {"kind": "imports", "target": "minisvc.models.Order", "evidence": "handlers.py:2"},
        {"kind": "imports", "target": "minisvc.storage.repo.OrderRepository", "evidence": "handlers.py:3"},
        {"kind": "instantiates", "target": "Order(...)", "evidence": "handlers.py:7-11"},
        {"kind": "calls", "target": "repo.save(order)", "evidence": "handlers.py:12"},
        {"kind": "calls", "target": "repo.get(order_id)", "evidence": "handlers.py:17"},
        {"kind": "calls", "target": "order_event(order, 'created')", "evidence": "handlers.py:13"},
        {"kind": "calls", "target": "order_event(order, 'read')", "evidence": "handlers.py:20"}
      ]
    },
    {
      "module": "minisvc.audit",
      "file": "minisvc/audit.py",
      "role": "in-memory audit event builder",
      "active_business_logic": true,
      "key_functions": ["order_event(order, action)"],
      "dependencies": [
        {"kind": "imports", "target": "minisvc.models.Order", "evidence": "audit.py:1"}
      ]
    },
    {
      "module": "minisvc.storage.repo",
      "file": "minisvc/storage/repo.py",
      "role": "SQLite repository",
      "active_business_logic": true,
      "key_classes": ["OrderRepository"],
      "key_functions": ["__init__", "init_schema", "save", "get"],
      "dependencies": [
        {"kind": "imports", "target": "sqlite3", "evidence": "repo.py:1"},
        {"kind": "imports", "target": "pathlib.Path", "evidence": "repo.py:2"},
        {"kind": "imports", "target": "minisvc.models.Order", "evidence": "repo.py:4"},
        {"kind": "instantiates", "target": "Path(database_path)", "evidence": "repo.py:9"},
        {"kind": "persists_to", "target": "SQLite orders table", "evidence": "repo.py:12-15 and repo.py:18-22"},
        {"kind": "calls", "target": "sqlite3.connect(self.database_path)", "evidence": "repo.py:12, repo.py:18, repo.py:25"},
        {"kind": "calls", "target": "Order(*row)", "evidence": "repo.py:30"}
      ]
    }
  ]
}
```

### CLI startup flow

1. Console script `minisvc` resolves to `minisvc.cli:main` in `pyproject.toml:6-7`.
2. `main(argv=None)` starts in `minisvc/cli.py:7`.
3. It reads process environment through `load_settings(os.environ)` in `cli.py:8`.
4. `load_settings` reads `MINISVC_DB`, defaulting to `orders.sqlite`, and `MINISVC_READONLY`, defaulting to false, in `config.py:10-13`.
5. CLI creates `OrderRepository(settings.database_path)` in `cli.py:9`.
6. `OrderRepository.__init__` stores `Path(database_path)` in `repo.py:8-9`.
7. CLI calls `repo.init_schema()` in `cli.py:10`.
8. `init_schema` connects to SQLite and creates the `orders` table if absent in `repo.py:11-15`.
9. CLI prints `minisvc ready at ...` and returns `0` in `cli.py:11-12`.

### HTTP create-order runtime flow

1. The canonical HTTP setup function is `register_routes(app, repo)` in `minisvc/api/routes.py:4`.
2. It binds `POST /orders` to `lambda payload: create_order(payload, repo)` in `routes.py:5`.
3. `create_order(payload, repo)` is defined in `minisvc/api/handlers.py:6`.
4. It builds an `Order` from `payload["order_id"]`, `payload["customer"]`, and `int(payload["total_cents"])` in `handlers.py:7-11`.
5. It persists the order through `repo.save(order)` in `handlers.py:12`.
6. `OrderRepository.save` opens SQLite and executes an insert into `orders(order_id, customer, total_cents)` in `repo.py:17-22`.
7. `create_order` returns a response dict with status, order ID, and an audit event from `order_event(order, "created")` in `handlers.py:13`.
8. `order_event` returns a dict with type, action, order ID, and total cents in `audit.py:4-10`.

There is no visible retry loop, readonly guard, or durable audit write on this path.

## Evidence

Observed repository files:

- `README.md`
- `pyproject.toml`
- `minisvc/__init__.py`
- `minisvc/api/__init__.py`
- `minisvc/api/routes.py`
- `minisvc/api/handlers.py`
- `minisvc/audit.py`
- `minisvc/cli.py`
- `minisvc/config.py`
- `minisvc/models.py`
- `minisvc/storage/__init__.py`
- `minisvc/storage/repo.py`

Commands and reads used:

- `find /workspace/in/repo -maxdepth 4 -type f | sort`
- Read all listed source files and `README.md`.
- Ran an AST inspection with `python3` over `/workspace/in/repo` to list imports, classes, functions, and calls. It confirmed:
  - `cli.py` imports `load_settings` and `OrderRepository`; calls `load_settings`, `OrderRepository`, and `init_schema`.
  - `routes.py` imports `create_order` and `get_order`; calls `app.post`, `app.get`, `create_order`, and `get_order`.
  - `handlers.py` imports `order_event`, `Order`, and `OrderRepository`; calls `Order`, `repo.save`, `repo.get`, and `order_event`.
  - `repo.py` imports `sqlite3`, `Path`, and `Order`; calls `sqlite3.connect`, `execute`, `fetchone`, and `Order`.

README comparison evidence:

- `README.md:5-8` says older design notes claimed readonly write blocking, SQLite write retries, and durable audit table.
- `README.md:10` says code is authoritative if docs and implementation disagree.
- Actual code reads `MINISVC_READONLY` in `config.py:13`, but no caller uses `settings.readonly` after `cli.py:8-10`.
- Actual save path `repo.py:17-22` performs a single insert with no retry loop.
- Actual audit function `audit.py:4-10` returns a dict only; storage schema in `repo.py:14` creates only an `orders` table.

## Conflicts or uncertainty

- I found no HTTP framework implementation in the repo. `register_routes(app, repo)` assumes an `app` object with `.post` and `.get`, but the concrete framework is outside this fixture.
- I did not execute runtime flows against an app or database because the branch asked for inspection only and no modification.
- `Settings.readonly` exists, but I found no enforcement edge from config to repository or handlers.
- Audit events are returned in API response dicts, but I found no persistence target for them.

## Recommendations

- In `architecture.md`, mark `__init__.py` files as package markers, not business logic.
- In `module_map.json`, model `minisvc.cli:main` and `minisvc.api.routes:register_routes` as the canonical entry points.
- Flag README design notes as stale where they claim readonly enforcement, write retries, and durable audit persistence.
- For runtime flow docs, state that `create_order` directly validates by indexing/casting only, then performs one SQLite insert and returns a non-persisted audit event.
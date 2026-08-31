# minisvc architecture

## Overview

`minisvc` is a small Python service with two adapters: a console bootstrap and an HTTP route-registration adapter. The implementation is authoritative over the older README design notes. Active business/runtime modules are `config.py`, `models.py`, `audit.py`, `storage/repo.py`, `api/handlers.py`, `api/routes.py`, and `cli.py`. `minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are package marker files, not business-logic modules.

## Modules and entry points

- `minisvc.cli:main` is the `pyproject.toml` console-script entry point. It loads settings, creates `OrderRepository`, initializes the schema, and prints readiness.
- `minisvc.config:load_settings` maps `MINISVC_DB` to the database path (default `orders.sqlite`) and parses `MINISVC_READONLY` into `Settings.readonly`.
- `minisvc.models:Order` is the dataclass containing `order_id`, `customer`, and `total_cents`.
- `minisvc.storage.repo:OrderRepository` owns SQLite schema creation, inserts, and parameterized reads.
- `minisvc.api.routes:register_routes` registers `POST /orders` and `GET /orders/<order_id>`.
- `minisvc.api.handlers:create_order` and `get_order` implement the request-level behavior.
- `minisvc.audit:order_event` only constructs a response dictionary; it is not an audit repository.

## Data flow

For create: an app invokes `register_routes`, the POST callback passes its payload to `create_order`, and the handler constructs an `Order` with `int(payload["total_cents"])`. `OrderRepository.save` inserts the record into SQLite. The response includes a generated `order_event` dictionary. For reads, `get_order` calls `OrderRepository.get`; it returns `missing` for no row or `ok` with `order.__dict__` for a hit, plus an in-memory read event.

## Storage

SQLite is opened directly by each repository method with `sqlite3.connect(self.database_path)`. `init_schema` creates only the `orders` table, with `order_id` as the primary key and non-null customer/total columns. Context managers commit successful writes and close connections. There is no migration layer, connection pool, audit table, or retry wrapper.

## Important runtime flow

CLI startup is `main -> load_settings -> OrderRepository -> init_schema -> readiness print`. HTTP create is `register_routes -> POST callback -> create_order -> Order -> save -> order_event -> response`. Route registration uses lambdas, so traceback inspection may pass through anonymous callbacks.

## Risks and extension points

- `Settings.readonly` is parsed but never consulted by route handlers or `OrderRepository.save`; writes are not blocked.
- `save` has no retry logic and exposes SQLite errors to its caller.
- Audit events are response-only dictionaries; no durable audit record is written.
- `payload[...]` access and `int(...)` provide limited validation: missing keys, malformed totals, unexpected types, and domain constraints can raise or pass through.
- The default relative `orders.sqlite` path depends on the process working directory; environment configuration is not validated.
- Natural extension points are a repository-level write policy/retry boundary, explicit request validation, and a separate durable audit repository/table. These should be added with tests around route and storage behavior.

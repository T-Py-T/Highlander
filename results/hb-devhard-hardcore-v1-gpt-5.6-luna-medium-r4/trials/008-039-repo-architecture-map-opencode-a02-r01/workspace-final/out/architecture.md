# minisvc Architecture

## Overview

`minisvc` is a small Python order service. The executable console script is declared in `pyproject.toml`; the HTTP adapter is framework-agnostic and receives an app object and repository through `register_routes`.

## Modules

- `minisvc.cli`: active startup code. Loads configuration, creates the repository, initializes SQLite, and prints readiness.
- `minisvc.config`: active environment-to-settings mapping for `MINISVC_DB` and `MINISVC_READONLY`.
- `minisvc.models`: active `Order` dataclass.
- `minisvc.storage.repo`: active SQLite persistence for the `orders` table.
- `minisvc.api.routes`: active route binding for `POST /orders` and `GET /orders/<order_id>`.
- `minisvc.api.handlers`: active request handling and response construction.
- `minisvc.audit`: active event-dictionary construction, but not audit persistence.

`minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are package marker/export files, not business-logic modules.

## Entry Points

- `minisvc.cli:main`, exposed as the `minisvc` console command.
- `minisvc.api.routes:register_routes(app, repo)`, the HTTP adapter setup function.
- The registered endpoints delegate to `minisvc.api.handlers:create_order` and `get_order`.

## Data Flow

At startup, `main` reads environment variables, constructs `OrderRepository`, and calls `init_schema`. For creation, the POST route passes a payload to `create_order`; required keys are read directly, `total_cents` is converted to an integer, and an `Order` is inserted. The response contains the ID and a generated event dictionary. Reads query SQLite and return either `missing` or the dataclass `__dict__` plus a read event.

## Storage

SQLite is opened independently with `sqlite3.connect` for each repository operation. The database path defaults to `orders.sqlite` and can be set with `MINISVC_DB`. The only schema is `orders(order_id primary key, customer not null, total_cents not null)`. There is no audit table, migration layer, transaction retry, or explicit durability policy beyond SQLite connection context managers.

## Risks and Extension Points

- `Settings.readonly` is parsed but never passed to or checked by the repository, so write operations remain possible in readonly mode.
- `OrderRepository.save` has no retry handling; SQLite errors and duplicate keys propagate through the handler.
- `order_event` only returns a dictionary. If audit persistence is required, add an injected audit repository/table and define failure semantics.
- `create_order` directly indexes payload keys and uses `int()`, so malformed or missing input can raise `KeyError` or `ValueError` rather than a structured client error. Add an API validation boundary.
- The CLI initializes schema, but the route registration API assumes a ready repository and does not create schema itself.
- The SQLite path is relative by default, making the runtime working directory part of deployment configuration.

The important create flow is: route registration -> `create_order` -> `Order` construction -> `repo.save` -> SQLite insert -> `order_event` response. No retry or audit write occurs in that flow.

# minisvc onboarding plan

## Recommended read order

1. Read `README.md` for the stated intent, while noting that it explicitly defers to implementation when they disagree.
2. Read `pyproject.toml` to identify the `minisvc.cli:main` console entry point.
3. Read `minisvc/config.py` and `minisvc/models.py` for runtime settings and the `Order` shape.
4. Read `minisvc/storage/repo.py` for the actual SQLite schema and persistence behavior.
5. Read `minisvc/api/routes.py`, then `minisvc/api/handlers.py` to follow HTTP registration into create/read flows.
6. Read `minisvc/audit.py` last among active modules to see what the returned event contains—and that it is not persisted.

The three `__init__.py` files are package markers and exports only; they are not active business-logic modules. Focus debugging and changes on the files above.

## Local run and test commands

From the repository root:

```sh
python3 -m minisvc.cli
python3 -m compileall minisvc
```

The project declares no dependencies and no test command or test suite is present in the fixture. For a quick repository smoke check, run:

```sh
MINISVC_DB=/tmp/minisvc-onboarding.sqlite python3 -m minisvc.cli
```

The CLI initializes the schema and prints its readiness line. HTTP behavior requires a host application implementing the `app.post` and `app.get` methods expected by `register_routes`.

## First trace point

Set the first breakpoint at `minisvc/api/handlers.py:create_order`, immediately before `repo.save(order)`. Inspect the raw payload, the constructed `Order`, the configured repository path, and the exception type if the insert fails. For startup-only failures, begin at `minisvc/cli.py:main` and step through `load_settings` and `OrderRepository.init_schema`.

## Safe first changes

1. Add focused input validation in or immediately before `create_order` that converts malformed/missing fields into deliberate client errors without changing the SQLite schema.
2. Add tests around `load_settings` defaults and `OrderRepository.get/save` using a temporary database path; this is low-risk and will expose the documented-but-unimplemented readonly and retry expectations before those policies are changed.

Avoid treating the README's readonly, retry, and durable-audit statements as implemented features: code inspection shows those are discrepancies, not current behavior.

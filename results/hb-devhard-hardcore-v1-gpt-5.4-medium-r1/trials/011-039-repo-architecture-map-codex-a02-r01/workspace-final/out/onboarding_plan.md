# New Engineer Onboarding Plan

## Read order

Start with the active runtime code in this order:

1. `README.md` for the service intent and the explicit note that code is authoritative.
2. `pyproject.toml` to find the console entry point.
3. `minisvc/cli.py` to understand bootstrap and schema setup.
4. `minisvc/config.py` to see environment inputs.
5. `minisvc/api/routes.py` to see the HTTP surface.
6. `minisvc/api/handlers.py` to see request handling and response shape.
7. `minisvc/storage/repo.py` to see actual persistence behavior.
8. `minisvc/audit.py` and `minisvc/models.py` for the simple shared types.

Treat these as non-business-logic files:

- `minisvc/api/__init__.py` is empty.
- `minisvc/storage/__init__.py` is empty.
- `minisvc/__init__.py` only declares `__all__`.

## Local run and test commands

Run the CLI bootstrap:

```sh
cd /workspace/in/repo
python -m minisvc.cli
```

Run with an explicit database path:

```sh
cd /workspace/in/repo
MINISVC_DB=/tmp/minisvc.sqlite python -m minisvc.cli
```

There are no tests in this fixture repository. For a quick manual check after bootstrapping, inspect the SQLite file with any local `sqlite3` client and verify that the `orders` table exists.

## First breakpoint or trace point

Set the first breakpoint in `minisvc/api/handlers.py` at `create_order`, before `repo.save(order)`.

Why this point:

- It shows the raw payload shape.
- It shows the `Order` object after coercion.
- It is the narrowest point before persistence and before the response audit event is created.

If you are tracing startup instead, break in `minisvc/cli.py` at `repo.init_schema()`.

## Two safe first changes

1. Add structured request validation in `create_order` so missing fields or bad `total_cents` values return controlled errors instead of throwing exceptions.
2. Enforce `Settings.readonly` on create paths, either in the handler/service layer or in the repository, because the flag already exists in config but is not active.

Both changes are localized, easy to test manually, and reduce the largest doc/code gaps without changing the domain model.

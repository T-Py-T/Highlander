# New Engineer Onboarding Plan

## What Is Runtime Code

Read and reason about these first because they drive actual behavior:

1. `minisvc/cli.py`
2. `minisvc/config.py`
3. `minisvc/storage/repo.py`
4. `minisvc/api/handlers.py`
5. `minisvc/api/routes.py`
6. `minisvc/audit.py`
7. `minisvc/models.py`

Treat these as non-business-logic files:

- `minisvc/__init__.py`
- `minisvc/api/__init__.py`
- `minisvc/storage/__init__.py`

## Recommended Read Order

1. `README.md`
2. `pyproject.toml`
3. `minisvc/models.py`
4. `minisvc/config.py`
5. `minisvc/storage/repo.py`
6. `minisvc/api/handlers.py`
7. `minisvc/api/routes.py`
8. `minisvc/cli.py`
9. `minisvc/audit.py`

This order moves from top-level intent to domain model, then storage, then request handling and bootstrapping.

## Local Run And Test Commands

Run from the repo root.

```bash
python -m pip install -e .
minisvc
```

Useful variations:

```bash
MINISVC_DB=/tmp/minisvc-orders.sqlite minisvc
python -m compileall minisvc
```

There are no automated tests in the fixture repository, so `compileall` is only a syntax smoke check.

## First Debugging Breakpoint Or Trace Point

Start with `minisvc/api/handlers.py` inside `create_order` just before `repo.save(order)`.

Why this point:

- It shows the raw payload-to-model conversion.
- It is where validation problems and integer conversion issues surface.
- It leads directly into the persistence boundary in `OrderRepository.save`.

If you are tracing startup instead, begin at `minisvc/cli.py:main` and step into `load_settings` and `repo.init_schema()`.

## Two Safe First Changes

1. Add explicit request validation and friendly error responses around missing keys and bad `total_cents` values in `minisvc/api/handlers.py`.
2. Enforce `MINISVC_READONLY` on the write path, either before `repo.save(order)` or inside `OrderRepository.save`.

Both changes are small, localized, and aligned with documented expectations.

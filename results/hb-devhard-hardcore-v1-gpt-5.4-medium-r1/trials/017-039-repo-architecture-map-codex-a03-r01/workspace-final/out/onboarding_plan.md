# minisvc Onboarding Plan

## Read Order

Read the code in this order:

1. `README.md` for the intended service shape and the explicit note that code wins over older design notes.
2. `pyproject.toml` to find the packaged CLI entry point.
3. `minisvc/cli.py` to understand startup and schema initialization.
4. `minisvc/config.py` to see the environment contract.
5. `minisvc/api/routes.py` to locate the HTTP surface.
6. `minisvc/api/handlers.py` to follow request behavior end to end.
7. `minisvc/storage/repo.py` to understand persistence and failure modes.
8. `minisvc/audit.py` and `minisvc/models.py` for the shared data structures.

Treat these as active runtime code:

- `minisvc/cli.py`
- `minisvc/config.py`
- `minisvc/api/routes.py`
- `minisvc/api/handlers.py`
- `minisvc/storage/repo.py`
- `minisvc/audit.py`
- `minisvc/models.py`

Treat these as package marker or dead-simple support files, not business logic:

- `minisvc/__init__.py`
- `minisvc/api/__init__.py`
- `minisvc/storage/__init__.py`

## Local Run And Test Commands

From `/workspace/in/repo`:

```bash
python3 -m minisvc.cli
```

Smoke-test the create and read flow directly through the handler layer:

```bash
python3 - <<'PY'
from minisvc.storage.repo import OrderRepository
from minisvc.api.handlers import create_order, get_order

repo = OrderRepository("orders.sqlite")
repo.init_schema()
print(create_order({"order_id": "demo-1", "customer": "Taylor", "total_cents": "2500"}, repo))
print(get_order("demo-1", repo))
PY
```

There are no automated tests in the fixture repository, so initial verification is by CLI startup and handler-level smoke tests.

## First Debugging Point

Set the first breakpoint or trace at `minisvc/api/handlers.py` inside `create_order()` before `repo.save(order)`.

Why this spot:

- It is the narrowest point where request payload, model construction, write behavior, and audit response generation all meet.
- It exposes the current lack of readonly enforcement and input validation immediately.

If you are tracing startup instead, use `minisvc/cli.py` at `repo.init_schema()`.

## Two Safe First Changes

1. Add explicit input validation and stable error responses in `create_order()` for missing fields and non-integer `total_cents`.
2. Enforce `MINISVC_READONLY` in the write path, either in `create_order()` or `OrderRepository.save()`, with a clear error contract.

Both changes are low-scope, locally testable, and improve correctness without changing the repository layout.

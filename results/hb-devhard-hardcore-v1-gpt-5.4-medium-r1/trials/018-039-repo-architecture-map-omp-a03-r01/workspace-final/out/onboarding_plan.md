# minisvc onboarding plan

## Read order
1. `README.md` — one-screen intent plus design claims to verify against code.
2. `pyproject.toml` — confirms the only published console entry point: `minisvc.cli:main`.
3. `minisvc/cli.py` — startup path and schema initialization.
4. `minisvc/config.py` — environment contract: `MINISVC_DB`, `MINISVC_READONLY`.
5. `minisvc/api/routes.py` then `minisvc/api/handlers.py` — route wiring, payload handling, and response shapes.
6. `minisvc/storage/repo.py` — SQLite schema and persistence behavior.
7. `minisvc/audit.py` and `minisvc/models.py` — simple helpers and the domain model.

## Active runtime code vs marker files
Active runtime code lives in `cli.py`, `config.py`, `models.py`, `audit.py`, `api/routes.py`, `api/handlers.py`, and `storage/repo.py`.

Do not spend review time on `minisvc/__init__.py`, `minisvc/api/__init__.py`, or `minisvc/storage/__init__.py` first; they are package markers or trivial exports, not business logic.

## Local run and test commands
Run the CLI bootstrap from the repo root:

```bash
python3 -c "import sys; sys.path.insert(0, '.'); from minisvc.cli import main; raise SystemExit(main())"
```

Smoke-test the create/read path from the repo root:

```bash
python3 -c "import sys,tempfile; from pathlib import Path; sys.path.insert(0,'.'); from minisvc.storage.repo import OrderRepository; from minisvc.api.handlers import create_order,get_order; td=tempfile.TemporaryDirectory(); db=str(Path(td.name)/'orders.sqlite'); repo=OrderRepository(db); repo.init_schema(); print(create_order({'order_id':'demo','customer':'Ada','total_cents':'7'}, repo)); print(get_order('demo', repo))"
```

No checked-in automated tests were found in this fixture repository, so start with the smoke check above before adding behavior changes.

## First breakpoint or trace point
Set the first breakpoint at `minisvc/api/handlers.py:6` in `create_order`.

Why here:
- It is the narrowest point where request payload shape, numeric coercion, repository writes, and audit-event construction all meet.
- You can inspect malformed payload behavior before the raw `KeyError`/`ValueError` escapes.
- One step deeper reaches `OrderRepository.save()` at `minisvc/storage/repo.py:17` if the issue is persistence.

## Two safe first changes
1. Add explicit request validation in `minisvc.api.handlers:create_order` so missing or invalid payload fields become stable error responses instead of raw exceptions.
2. Enforce `Settings.readonly` on the write path, either before `repo.save(order)` or inside repository writes, because the config flag already exists but is currently ignored.

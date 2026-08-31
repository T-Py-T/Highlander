# minisvc onboarding plan

## Recommended read order

1. `README.md` and `pyproject.toml` for the intended surface and console-script mapping; treat README design notes as claims to verify, not implementation truth.
2. `minisvc/cli.py` and `minisvc/config.py` to see process startup and environment interpretation.
3. `minisvc/api/routes.py`, then `minisvc/api/handlers.py` to follow HTTP registration into create/read behavior.
4. `minisvc/models.py` for the data shape.
5. `minisvc/storage/repo.py` for the actual SQLite schema and persistence boundaries.
6. `minisvc/audit.py` while checking the discrepancy that events are constructed but not stored.

The empty `minisvc/api/__init__.py` and `minisvc/storage/__init__.py`, and the one-line `minisvc/__init__.py`, are package markers/metadata rather than active runtime business logic.

## Local run and test commands

From the repository root (`/workspace/in/repo` in this fixture):

```sh
PYTHONPATH=. python3 -c 'from minisvc.cli import main; raise SystemExit(main())'
python3 -m compileall -q minisvc
```

The first command exercises CLI startup and creates the configured SQLite schema (use a temporary working directory or set `MINISVC_DB` to avoid an unintended file). There is no test suite or HTTP server implementation in the fixture. A focused handler smoke test can be run without a web framework:

```sh
PYTHONPATH=. python3 -c 'import tempfile; from minisvc.storage.repo import OrderRepository; from minisvc.api.handlers import create_order, get_order; p=tempfile.mktemp(suffix=".sqlite"); r=OrderRepository(p); r.init_schema(); print(create_order({"order_id":"o1","customer":"A","total_cents":"125"}, r)); print(get_order("o1", r))'
```

## First debugging trace point

Set the first breakpoint at `minisvc.api.handlers:create_order`, line 7, or trace into `OrderRepository.save` at `minisvc/storage/repo.py`, line 17. This captures payload conversion before the SQLite write and is the shortest path for create-order failures. For startup/configuration issues, begin at `minisvc.cli:main`, line 8.

## Safe first changes

1. Add focused validation around `create_order` for missing fields, empty identifiers, and invalid/non-positive `total_cents`, with tests using a fake repository. This is localized and does not change the storage schema.
2. Add a repository-level readonly policy and tests proving `save` and schema initialization are rejected when enabled; wire the existing `Settings.readonly` from `cli.py` into that policy. Make the behavior explicit before changing retry or audit semantics.

Do not begin by editing package marker files. Also do not assume the README's retry and durable-audit statements are present: the current code saves once and only returns an in-memory event dictionary.

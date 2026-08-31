# minisvc onboarding plan

## Recommended read order

1. Read `README.md` first, treating its final sentence as the rule that code wins over older notes.
2. Read `pyproject.toml` to find the executable entry point: `minisvc.cli:main`.
3. Read `minisvc/cli.py` and `minisvc/config.py` together to understand startup and environment inputs.
4. Read `minisvc/models.py`, then `minisvc/storage/repo.py` for the `Order` shape and SQLite schema/queries.
5. Read `minisvc/api/routes.py`, followed by `minisvc/api/handlers.py`, to follow HTTP registration into application behavior.
6. Read `minisvc/audit.py` last when tracing response events and checking the difference between event construction and durable audit persistence.

The active runtime/business files are the seven modules above. `minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` are package marker files, not business logic. There are no tests in the fixture.

## Local run and test commands

From the repository root:

```sh
python -m minisvc.cli
# or, after installing the project:
minisvc

MINISVC_DB=/tmp/minisvc-orders.sqlite python -m minisvc.cli
python -m compileall minisvc
```

There is no test suite or HTTP server command in this repository. To exercise the API, provide an application object with `post` and `get` methods and call `minisvc.api.routes.register_routes(app, repo)`; alternatively, unit-test `create_order` and `get_order` with a temporary SQLite database.

## First debugging trace point

Set the first breakpoint at `minisvc/api/handlers.py:create_order`, then step into `OrderRepository.save` at `minisvc/storage/repo.py:17`. This captures raw payload handling, integer conversion, model construction, SQL persistence, and the response event. For startup issues, begin at `minisvc/cli.py:main` and inspect the `Settings` value immediately after `load_settings(os.environ)`.

## Safe first changes

1. Add focused validation/error mapping around `create_order` without changing the repository schema: reject missing fields and invalid or out-of-range `total_cents`, and return a stable client error. Cover it with unit tests using a temporary database.
2. Add observability-only logging or a dry-run diagnostic command around `main` and repository calls, documenting the resolved database path. Do not silently alter persistence semantics.

Avoid implementing the README's read-only, retry, or durable-audit claims as an unreviewed first change: each changes runtime semantics and needs explicit tests and a failure/transaction policy.

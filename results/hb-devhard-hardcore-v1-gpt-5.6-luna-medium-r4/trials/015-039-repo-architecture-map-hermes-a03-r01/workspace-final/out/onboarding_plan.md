# minisvc onboarding plan

## Recommended read order

1. Read `README.md` and `pyproject.toml`, treating the README design bullets as claims to verify rather than current behavior.
2. Read active runtime code in `minisvc/config.py` and `minisvc/models.py`.
3. Read `minisvc/storage/repo.py` to understand the SQLite schema and transaction boundaries.
4. Read `minisvc/api/handlers.py`, then `minisvc/api/routes.py` to follow HTTP data flow.
5. Read `minisvc/cli.py` for the console startup path.
6. Skim `minisvc/__init__.py`, `minisvc/api/__init__.py`, and `minisvc/storage/__init__.py` only as package markers; they contain no business logic.

## Local run and test commands

From the repository root:

```sh
python3 -m minisvc.cli
# or, after installing the project in a virtual environment:
# minisvc
python3 -m compileall minisvc
python3 -m unittest discover
```

The fixture has no test files and `cli.py` has no `if __name__ == "__main__"` launcher, so `python3 -m minisvc.cli` compiles/imports but does not invoke `main`. To exercise startup without changing source, use:

```sh
python3 -c 'from minisvc.cli import main; raise SystemExit(main())'
```

Set `MINISVC_DB=/tmp/orders.sqlite` to avoid relying on the current directory. There are no declared third-party dependencies.

## First trace point

Set a breakpoint or trace at `minisvc.api.handlers:create_order`, immediately before `repo.save(order)`. This is the first point where parsed request data becomes an `Order` and the create flow crosses into persistence. For CLI issues, start at `minisvc.cli:main` and step through `load_settings` and `init_schema`.

## Safe first changes

- Add pure input validation around `create_order` (required keys and non-negative integer `total_cents`) with focused tests; do not alter the repository schema.
- Add tests that characterize `load_settings` defaults/overrides and `OrderRepository.get/save` using a temporary SQLite file. These are low-risk changes and will expose the unused readonly setting and missing retry/audit behavior.

Avoid treating package marker files as extension points: active behavior lives in the modules listed above. Changes to readonly enforcement, retries, or audit durability should be designed as explicit repository/handler behavior and covered by integration tests.

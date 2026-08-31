# Onboarding plan

1. Read `README.md` first, treating its older design notes as hypotheses rather than guarantees.
2. Read `pyproject.toml` to find the console entry point.
3. Read active runtime code in this order: `minisvc/cli.py` -> `minisvc/config.py` -> `minisvc/storage/repo.py` -> `minisvc/models.py` -> `minisvc/api/routes.py` -> `minisvc/api/handlers.py` -> `minisvc/audit.py`.
4. Inspect the three `__init__.py` files last only to understand package markers/exports; they contain no business logic.
5. Review `doc_code_discrepancies.csv` and `risk_register.csv` before changing behavior, especially around readonly, retries, and audit persistence.

Local commands (from the repository root):

```sh
python -m pip install -e .
minisvc
python -c 'from minisvc.config import load_settings; print(load_settings({"MINISVC_DB": ":memory:"}))'
python -m compileall minisvc
```

There are no tests or test dependency declarations in this fixture. For a smoke test of persistence, use a temporary path and call `OrderRepository.init_schema`, `save`, and `get` from a short Python script; avoid creating `orders.sqlite` in the checkout unless desired. The CLI initializes a database but does not start an HTTP server. The API requires an external app object implementing `post` and `get`.

First debugging trace point: set a breakpoint in `minisvc.api.handlers:create_order` at the `Order(...)` construction and step into `repo.save`; this reveals payload conversion, validation gaps, SQL persistence, and the response-only audit event. For startup issues, begin at `minisvc.cli:main` and inspect `settings.database_path` before `init_schema()`.

Two safe first changes:

- Add focused tests (without changing production behavior) for `load_settings`, schema round-trip, missing orders, and malformed create payloads; these document current contracts.
- Add explicit input validation/error mapping in a separate handler boundary for required fields and non-negative `total_cents`, preserving the repository API and covering it with tests.

Do not initially change readonly, retry, or audit semantics without confirming the intended contract: the README promises all three, but the current implementation enforces none of them. Package marker files are not useful first modification targets.

Outcome: I found three doc/code discrepancies. README design notes claim readonly write blocking, SQLite write retries, and durable audit persistence, but the code does not implement those behaviors.

## Scope

I inspected only `/workspace/in/repo`. I did not modify files and did not use the internet.

Files inspected:
- `/workspace/in/repo/README.md`
- `/workspace/in/repo/pyproject.toml`
- `/workspace/in/repo/minisvc/config.py`
- `/workspace/in/repo/minisvc/cli.py`
- `/workspace/in/repo/minisvc/api/routes.py`
- `/workspace/in/repo/minisvc/api/handlers.py`
- `/workspace/in/repo/minisvc/audit.py`
- `/workspace/in/repo/minisvc/storage/repo.py`
- `/workspace/in/repo/minisvc/models.py`
- package marker files: `/workspace/in/repo/minisvc/__init__.py`, `/workspace/in/repo/minisvc/api/__init__.py`, `/workspace/in/repo/minisvc/storage/__init__.py`

## Findings

```csv
topic,doc_claim,code_observed,discrepancy,evidence
readonly enforcement,"README says `MINISVC_READONLY=1` blocks all write paths.","`load_settings` parses `MINISVC_READONLY` into `Settings.readonly`, but `cli.main` ignores `settings.readonly`; `OrderRepository.init_schema` and `OrderRepository.save` write to SQLite with no readonly guard; `create_order` calls `repo.save(order)` unconditionally.","Documented readonly blocking is not enforced. The env var is parsed but not used to block schema creation or order writes.","README.md:5-8; config.py:4-14; cli.py:7-11; api/handlers.py:6-13; storage/repo.py:11-22"
retry behavior,"README says `create_order` retries failed SQLite writes twice before returning an error response.","`create_order` constructs an `Order`, calls `repo.save(order)` once, and returns a created response. There is no loop, retry helper, try/except, or error response mapping in `create_order` or `OrderRepository.save`.","Documented retry behavior is absent. SQLite write failures would propagate rather than be retried twice and converted to an error response.","README.md:5-8; api/handlers.py:6-13; storage/repo.py:17-22"
audit persistence,"README says audit events are stored in a durable audit table.","`order_event` only builds and returns a dict. `create_order` and `get_order` include that dict in HTTP responses. `init_schema` creates only an `orders` table; no audit table or audit insert exists in the repository code.","Documented durable audit persistence is absent. Audit events are response payload data, not persisted records.","README.md:5-8; audit.py:4-10; api/handlers.py:12-20; storage/repo.py:11-22"
```

## Evidence

- `/workspace/in/repo/README.md:5-10` labels the three claims as “Design notes from an older implementation” and says the code is authoritative when docs and implementation disagree.
- `/workspace/in/repo/minisvc/config.py:10-14` reads `MINISVC_READONLY`, but no inspected write path checks `Settings.readonly`.
- `/workspace/in/repo/minisvc/cli.py:7-11` loads settings, builds `OrderRepository(settings.database_path)`, runs `repo.init_schema()`, and returns success.
- `/workspace/in/repo/minisvc/api/handlers.py:6-13` defines `create_order`; it calls `repo.save(order)` once and returns `{"status": "created", ...}`.
- `/workspace/in/repo/minisvc/storage/repo.py:11-22` writes schema and inserts orders with direct `sqlite3.connect(...).execute(...)` calls. It has no readonly check, retry loop, audit table creation, or audit insert.
- `/workspace/in/repo/minisvc/audit.py:4-10` returns an in-memory event dict only.
- A repository search for `readonly|MINISVC_READONLY|retry|retries|audit|order_event|create_order|save|sqlite|orders` found relevant matches only in the files cited above.

## Conflicts or uncertainty

- No separate design notes file was present under `/workspace/in/repo`; the only design notes found were in `README.md:5-8`.
- I did not run the service. The discrepancies above are static-code findings backed by file contents.
- `README.md:10` explicitly warns that the code is authoritative, so these are known stale-design-note conflicts rather than hidden implementation bugs.

## Recommendations

- For `doc_code_discrepancies.csv`, include the three CSV rows above.
- Update README design notes to say:
  - readonly is parsed but not enforced;
  - `create_order` does not retry writes;
  - audit events are returned in responses but not persisted.
- If the old design is still desired, add tests first for readonly blocking, retry semantics, and audit persistence, then implement those paths in code.

## Contract amendments received

None.
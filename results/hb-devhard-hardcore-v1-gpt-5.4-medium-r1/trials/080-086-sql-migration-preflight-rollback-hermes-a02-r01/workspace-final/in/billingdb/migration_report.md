# Billing migration repair report

## Files delivered
- `migration.sql`: rebuilt as an explicit transaction-safe SQLite migration.
- `preflight_report.md`: documents pre-migration counts and orphan payment discovery.
- `rollback.sql`: restores the legacy table shapes and merges preserved orphan payments back into `payments`.
- `postcheck.sql`: verifies row counts, orphan preservation, status defaults, invalid references, and foreign key integrity.

## Repair summary
- Preserves all invoice rows and all valid payment rows from `schema.sql`.
- Preserves historical invoice `created_at` values during the `invoices` rebuild.
- Adds `invoices.status TEXT NOT NULL DEFAULT 'open'` while backfilling existing rows with `open`.
- Copies orphan payments into `payment_orphans` using `INSERT OR IGNORE`, so rerunning the migration does not duplicate `p4`.
- Rebuilds `payments` with a foreign key to `invoices(id)` so future `invoice_id` values must reference a real invoice.
- Wraps the migration and rollback in explicit transactions and restores `PRAGMA foreign_keys = ON` afterward.

## Validation results
Validated with Python's built-in SQLite engine by applying `schema.sql`, running `migration.sql` twice, executing `postcheck.sql`, and then running `rollback.sql` twice.

Observed results after running `migration.sql` twice:
- `invoices` row count stayed `3`.
- `payments` row count stayed `3`.
- `payment_orphans` row count stayed `1`.
- preserved orphan `p4` was present in `payment_orphans` exactly once.
- `invoice_status_null_count` was `0`.
- `invoice_status_open_count` was `3`.
- `invalid_payment_references` was `0`.
- `PRAGMA foreign_key_check` returned no rows.
- invoice `inv1` retained historical `created_at = 2024-01-03T10:00:00Z`.

Observed results after `rollback.sql`:
- table shapes returned to `invoices(id, customer_id, total_cents, created_at)` and `payments(id, invoice_id, amount_cents, created_at)`.
- `payments` contained all four original payment rows again, including `p4`.
- only `invoices` and `payments` remained; `payment_orphans` was removed.
- a second rollback run also completed without error.

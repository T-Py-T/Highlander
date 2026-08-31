# Billing migration repair report

## Files changed
- `in/billingdb/migration.sql`
- `in/billingdb/preflight_report.md`
- `in/billingdb/rollback.sql`
- `in/billingdb/postcheck.sql`

## What the repaired migration does
- Runs inside `BEGIN IMMEDIATE ... COMMIT`.
- Creates `payment_orphans` if needed.
- Copies orphan payments into `payment_orphans` with a reason.
- Preserves invoice rows and historical `created_at` values.
- Rebuilds `invoices` with `status TEXT NOT NULL DEFAULT 'open'`.
- Rebuilds `payments` with a foreign key to `invoices(id)`.
- Restores `PRAGMA foreign_keys = ON` after the migration.

## Validation run
A local SQLite replay against `schema.sql` showed:
- after migration: 3 invoices, 3 payments, 1 payment orphan
- preserved orphan: `p4`
- invalid payment references after migration: 0
- `PRAGMA foreign_key_check`: no rows
- second migration run: same row counts and no duplicate data
- rollback restored table shapes to:
  - `invoices(id, customer_id, total_cents, created_at)`
  - `payments(id, invoice_id, amount_cents, created_at)`
- rollback restored `p4` to `payments`

## Notes
- `schema.sql` and `migration_policy.md` were left unchanged.
- The package uses SQLite-only SQL.

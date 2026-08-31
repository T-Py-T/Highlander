# Migration Report

## Repaired files
- `migration.sql`
- `preflight_report.md`
- `rollback.sql`
- `postcheck.sql`

## What changed in `migration.sql`
- Wrapped the migration in an explicit transaction with `BEGIN IMMEDIATE` / `COMMIT`.
- Restored `PRAGMA foreign_keys = ON` after the migration.
- Added idempotent creation of `payment_orphans`.
- Preserved orphan payments by copying missing invoice references into `payment_orphans` with a reason.
- Rebuilt `invoices` with `status TEXT NOT NULL DEFAULT 'open'` while preserving `id`, `customer_id`, `total_cents`, and historical `created_at`.
- Rebuilt `payments` so only valid invoice references remain in the live table.
- Added a foreign key from `payments.invoice_id` to `invoices.id` and created an index on `payments(invoice_id)`.
- Used `INSERT OR IGNORE` for orphan capture so reruns do not duplicate `payment_orphans` rows.

## Rollback behavior
- Restores `invoices(id, customer_id, total_cents, created_at)`.
- Restores `payments(id, invoice_id, amount_cents, created_at)`.
- Merges preserved rows from `payment_orphans` back into `payments`.
- Drops `payment_orphans` during rollback so the old package shape is restored.

## Verification performed
Validated with Python's SQLite 3.40.1 against the provided `schema.sql` data.

### After first migration
- invoices: 3 rows
- payments: 3 rows
- payment_orphans: 1 row
- orphan preserved: `p4`
- all invoice statuses: `open`
- null invoice statuses: 0
- foreign key violations: 0

### After second migration run
- invoices: 3 rows
- payments: 3 rows
- payment_orphans: 1 row
- duplicate orphan rows introduced: no
- foreign key violations: 0

### After rollback
- `invoices` columns restored to: `id, customer_id, total_cents, created_at`
- `payments` columns restored to: `id, invoice_id, amount_cents, created_at`
- restored payment rows: `p1, p2, p3, p4`
- `payment_orphans` removed

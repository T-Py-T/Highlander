# Billing migration repair report

## What was fixed

- Wrapped the migration in an explicit transaction.
- Added creation and population of `payment_orphans`.
- Preserved orphan payment `p4` instead of deleting it.
- Rebuilt `payments` with a foreign key to `invoices(id)`.
- Preserved all invoice and valid payment business rows.
- Preserved invoice `created_at` values.
- Added `invoices.status TEXT NOT NULL DEFAULT 'open'`.
- Made reruns safe by avoiding duplicate orphan moves and rebuilding target tables deterministically.
- Added rollback SQL that restores the original `invoices` and `payments` shapes and merges orphan rows back into `payments`.
- Added post-migration verification SQL and a preflight report.

## Validation performed

Validation was executed with Python's built-in SQLite engine (`sqlite3`, SQLite 3.40.1) because the `sqlite3` shell binary is not installed in this environment.

### After `schema.sql` then `migration.sql`

- invoices count = 3
- payments count = 3
- payment_orphans count = 1
- `p4` preserved in `payment_orphans` = yes
- invoice `status` null count = 0
- invoice `status <> 'open'` count = 0
- invoice `created_at` drift count = 0
- rows in `payments` with missing invoices = 0
- `PRAGMA foreign_key_check` returned no violations
- inserting a new payment with a missing invoice failed with `FOREIGN KEY constraint failed`

### After running `migration.sql` a second time

- invoices count remained 3
- payments count remained 3
- payment_orphans count remained 1
- `p4` remained present exactly once in `payment_orphans`
- no invalid `payments.invoice_id` values were introduced

### After `schema.sql` then `migration.sql` then `rollback.sql`

- `invoices` columns restored to: `id, customer_id, total_cents, created_at`
- `payments` columns restored to: `id, invoice_id, amount_cents, created_at`
- invoice row count = 3
- payment row count = 4
- orphan payment `p4` was restored into `payments`
- `payment_orphans` table no longer existed after rollback

## Environment note

The user-supplied `<HOME>/.../billingdb` path is not mounted in this Linux workspace, and `/Users` is read-only here. The editable workspace mirror used for the repair is:

`/workspace/in/billingdb`

# Billing migration report

## Fixed problems
- wrapped the migration in an explicit transaction
- preserved invoices instead of deleting rows
- preserved invoice `created_at`
- added `invoices.status TEXT NOT NULL DEFAULT 'open'`
- moved orphan payments into `payment_orphans` before enforcing referential safety
- kept orphan payment `p4`
- rebuilt `payments` with a foreign key to `invoices(id)`
- restored `PRAGMA foreign_keys = ON` before commit
- added rollback and postcheck scripts

## Idempotence notes
- orphan moves use `INSERT OR IGNORE`, so `payment_orphans` does not duplicate rows
- orphan cleanup deletes only rows already captured in `payment_orphans`
- table rebuilds recreate the target schema from current live data, so a second run keeps row counts stable and does not duplicate invoice or payment rows

## Expected result after migration
- `invoices`: 3 rows, now with `status`
- `payments`: 3 rows, all linked to valid invoices
- `payment_orphans`: 1 row (`p4`)

## Expected result after rollback
- `invoices(id, customer_id, total_cents, created_at)` restored
- `payments(id, invoice_id, amount_cents, created_at)` restored
- orphan payment `p4` moved back into `payments`

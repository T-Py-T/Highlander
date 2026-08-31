# Migration Report

## Delivered Files

- `migration.sql`: explicit transaction, invoice rebuild with `status`, orphan preservation, and referential enforcement
- `rollback.sql`: restores the legacy table shapes and merges preserved orphans back into `payments`
- `postcheck.sql`: validates row counts, orphan preservation, default statuses, and foreign-key integrity
- `preflight_report.md`: documents source counts and the orphan payment that must be preserved

## Key Repairs

- removed the destructive orphan-payment delete from the draft
- preserved all invoices, payments tied to real invoices, and historical `created_at` values
- added `payment_orphans` so `p4` is retained instead of dropped
- enforced `payments.invoice_id` references with a foreign key in the rebuilt `payments` table
- wrapped the migration in an explicit transaction and restored `PRAGMA foreign_keys` after the rebuild
- made reruns non-duplicating by rebuilding from current tables and using `payment_orphans` / `_invoice_status_shadow` as stable migration state

## Expected Result On `schema.sql`

- `invoices`: 3 rows, all with `status = 'open'`
- `payments`: 3 rows referencing valid invoices only
- `payment_orphans`: 1 row containing `p4`
- `rollback.sql` returns the schema to `invoices(id, customer_id, total_cents, created_at)` and `payments(id, invoice_id, amount_cents, created_at)` while restoring `p4` to `payments`

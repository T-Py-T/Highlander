# Billing migration preflight report

Source: `schema.sql` in this package.

## Findings

- `invoices` has 3 rows: `inv1`, `inv2`, and `inv3`.
- `payments` has 4 rows: `p1`, `p2`, `p3`, and `p4`.
- `p4` is an orphan: its `invoice_id` is `missing-invoice`, which is absent from `invoices`.
- The source tables do not enforce a foreign key from `payments.invoice_id` to `invoices.id`.
- `invoices` has no `status` column; the migration adds `status TEXT NOT NULL DEFAULT 'open'`.
- All source invoice `created_at` values must be copied unchanged.

## Planned preservation

- All three invoices are copied unchanged, including their historical `created_at` values.
- Valid payments `p1`–`p3` remain in `payments`.
- Orphan `p4` is copied, not deleted, to `payment_orphans` with the same `id`, `invoice_id`, `amount_cents`, and `created_at`, plus reason `invoice_id does not reference an existing invoice`.
- The rebuilt `payments` table has a foreign key to `invoices(id)`, so future invalid references are rejected.

## Safety and rerun notes

`migration.sql` enables foreign keys, uses an explicit `BEGIN IMMEDIATE`/`COMMIT` transaction, stages rows before replacing tables, and restores `PRAGMA foreign_keys = ON` after commit. Its `payment_orphans` insert is `INSERT OR IGNORE`, and staging tables are dropped before creation, so a completed rerun does not duplicate rows or orphan records.

The preflight can be independently verified with:

```sql
SELECT 'invoices' AS table_name, COUNT(*) AS row_count FROM invoices
UNION ALL SELECT 'payments', COUNT(*) FROM payments
UNION ALL
SELECT 'orphan_payments', COUNT(*)
FROM payments AS p LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;
```

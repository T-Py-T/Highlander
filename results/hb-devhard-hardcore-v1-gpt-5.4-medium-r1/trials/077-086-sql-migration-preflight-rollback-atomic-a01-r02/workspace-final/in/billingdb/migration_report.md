# Billing migration repair report

## Files
- `migration.sql`: transaction-safe, idempotent migration.
- `preflight_report.md`: source counts and orphan note.
- `rollback.sql`: restores the old `invoices` and `payments` shapes.
- `postcheck.sql`: checks counts, status defaults, orphan preservation, and foreign keys.

## What changed
- Added an explicit transaction with `BEGIN IMMEDIATE` and `COMMIT`.
- Added `payment_orphans` and moved orphan payments there before live-table foreign-key enforcement.
- Kept invoice `created_at` values during the rebuild.
- Added `invoices.status TEXT NOT NULL DEFAULT 'open'`.
- Rebuilt `payments` with a foreign key to `invoices(id)` so new rows must point to real invoices.
- Added rollback SQL that puts preserved orphan payments back into the legacy `payments` table.

## Expected data after migration
- `invoices`: 3 rows, all with non-null `status`.
- `payments`: 3 valid rows.
- `payment_orphans`: 1 row, preserving `p4`.

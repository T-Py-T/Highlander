# Billing Migration Report

## Changes
- Replaced the unsafe draft migration with an explicit transaction that preserves invoice rows, preserves `created_at`, adds `invoices.status TEXT NOT NULL DEFAULT 'open'`, quarantines legacy orphan payments in `payment_orphans`, and rebuilds `payments` with a foreign key to `invoices(id)`.
- Added `preflight_report.md` with the source row counts and the identified orphan payment `p4`.
- Added `postcheck.sql` with row-count, orphan-preservation, status, and foreign-key validation queries.
- Added `rollback.sql` that restores the legacy `invoices(id, customer_id, total_cents, created_at)` and `payments(id, invoice_id, amount_cents, created_at)` table shapes and merges orphan rows back into `payments`.

## Verification
Executed the package against a temporary SQLite database initialized from `schema.sql`.

1. Applied `migration.sql` once.
   - `invoices` rows: 3
   - `payments` rows: 3
   - `payment_orphans` rows: 1
   - `payment_orphans` preserved `p4`
   - `invoices.status` null rows: 0
   - `PRAGMA foreign_key_check`: no rows
2. Applied `migration.sql` a second time.
   - Row counts stayed stable: `invoices=3`, `payments=3`, `payment_orphans=1`
   - `p4` remained present exactly once in `payment_orphans`
3. Attempted to insert a payment referencing a missing invoice after migration.
   - SQLite rejected the insert with `FOREIGN KEY constraint failed`
4. Applied `rollback.sql` after migration.
   - Restored `invoices` columns to `id, customer_id, total_cents, created_at`
   - Restored `payments` columns to `id, invoice_id, amount_cents, created_at`
   - Restored 4 payment rows, including `p4` back in `payments`
   - Removed `payment_orphans`

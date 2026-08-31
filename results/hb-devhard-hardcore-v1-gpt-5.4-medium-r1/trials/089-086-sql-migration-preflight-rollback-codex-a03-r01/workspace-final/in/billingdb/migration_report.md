# Billing Migration Repair Report

## What changed

- Replaced the unsafe draft migration with an explicit transaction using `BEGIN IMMEDIATE` / `COMMIT`.
- Added `payment_orphans` preservation before rebuilding `payments`.
- Rebuilt `payments` with `FOREIGN KEY (invoice_id) REFERENCES invoices(id)` so future rows must reference valid invoices.
- Preserved all invoice rows and historical `created_at` values while adding `status TEXT NOT NULL DEFAULT 'open'`.
- Added a rollback script that restores the legacy `invoices` and `payments` table shapes and reinserts orphan payments into legacy `payments`.
- Added a postcheck script that verifies row counts, orphan preservation, default status population, and foreign-key integrity.

## Expected result after migration

- `invoices` contains 3 rows with the new `status` column populated as `open`.
- `payments` contains 3 rows: `p1`, `p2`, and `p3`.
- `payment_orphans` contains preserved orphan payment `p4`.

## Expected result after rollback

- `invoices` is restored to `invoices(id, customer_id, total_cents, created_at)`.
- `payments` is restored to `payments(id, invoice_id, amount_cents, created_at)`.
- Legacy `payments` once again includes `p4`.

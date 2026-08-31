# Billing migration report

## Repaired artifacts
- Updated `migration.sql` to run inside `BEGIN IMMEDIATE … COMMIT`.
- Added `payment_orphans` preservation before referential enforcement.
- Rebuilt `invoices` with `status TEXT NOT NULL DEFAULT 'open'`.
- Rebuilt `payments` with a foreign key to `invoices` so future invalid `invoice_id` values are rejected.
- Added `rollback.sql` to restore the legacy table shapes.
- Added `postcheck.sql` to verify row counts, orphan preservation, status defaults, preserved timestamps, and foreign-key integrity.
- Added `preflight_report.md` documenting the fixture counts and the known orphan `p4`.

## Verification performed
Using Python `sqlite3` against a fresh database initialized from `schema.sql`:
1. Ran `migration.sql` once.
2. Confirmed post-migration state:
   - `invoices`: 3 rows.
   - `payments`: 3 valid rows (`p1`, `p2`, `p3`).
   - `payment_orphans`: 1 preserved row (`p4`).
   - invoice `created_at` values remained `2024-01-03T10:00:00Z`, `2024-01-04T10:00:00Z`, `2024-01-05T10:00:00Z`.
   - `PRAGMA foreign_key_check` returned no rows.
3. Ran `migration.sql` a second time.
4. Confirmed the second run was idempotent: row contents for `invoices`, `payments`, and `payment_orphans` were unchanged.
5. Attempted `INSERT INTO payments(id, invoice_id, amount_cents, created_at) VALUES ('p-bad', 'missing-invoice', 1, '2024-02-01T00:00:00Z')` after migration.
6. Confirmed SQLite rejected it with `FOREIGN KEY constraint failed`.
7. Ran `rollback.sql` after migration.
8. Confirmed rollback restored only the legacy tables and shapes:
   - `invoices(id, customer_id, total_cents, created_at)`
   - `payments(id, invoice_id, amount_cents, created_at)`
9. Confirmed rollback restored `p4` to `payments` without deleting it.

## Result
The migration package now preserves invoices and payments, moves orphan payment `p4` into `payment_orphans` during migration, enforces future referential safety on `payments.invoice_id`, and rolls back to the old schema shape without data loss.

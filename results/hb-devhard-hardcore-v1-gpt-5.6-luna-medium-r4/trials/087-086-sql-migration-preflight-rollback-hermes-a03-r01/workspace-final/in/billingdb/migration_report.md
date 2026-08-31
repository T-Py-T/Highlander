# Billing migration report

## Package repaired

- `migration.sql` now runs inside `BEGIN IMMEDIATE`/`COMMIT`.
- Foreign-key enforcement is disabled only for the SQLite table-rebuild window and is restored with `PRAGMA foreign_keys = ON` before the script ends.
- Existing orphan payments are copied to `payment_orphans` before rebuilding `payments`; no orphan is deleted.
- The replacement `payments` table has a foreign key from `invoice_id` to `invoices(id)`.
- The replacement `invoices` table adds `status TEXT NOT NULL DEFAULT 'open'`.
- Invoice IDs, amounts, customers, and historical `created_at` values are copied unchanged.
- Repeated execution uses `IF NOT EXISTS` and `INSERT OR IGNORE` for the archive/staging operations, so the supplied fixture is not duplicated or corrupted on a second run.
- `rollback.sql` restores both legacy four-column table shapes and puts archived orphans back into `payments`, including `p4`.
- `postcheck.sql` checks row counts, status values, orphan preservation, valid payment references, the installed foreign key, foreign-key violations, and historical invoice timestamps.

## Verification performed

The supplied `schema.sql` was loaded into a fresh SQLite database, followed by `migration.sql` twice, then `rollback.sql`.

### After the first migration

- `invoices`: 3 rows.
- `payments`: 3 valid rows (`p1`, `p2`, `p3`).
- `payment_orphans`: 1 row (`p4`, invoice ID `missing-invoice`, amount `700`, original timestamp retained).
- All 3 invoices have `status = 'open'`.
- `payments.invoice_id` has a foreign key to `invoices.id`.
- `PRAGMA foreign_key_check` returned no rows.

### After the second migration execution

The invoice rows, valid payment rows, and the single archived `p4` row were byte-for-byte identical to the first post-migration result; no duplicate rows were created.

### After rollback

- `invoices` columns were exactly `id, customer_id, total_cents, created_at`.
- `payments` columns were exactly `id, invoice_id, amount_cents, created_at`.
- `payments` contained all 4 original payments, including `p4`.
- `payment_orphans` was removed.

The source files `schema.sql` and `migration_policy.md` were not modified.

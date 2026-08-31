# Billing migration preflight

## Source inspected

- `schema.sql` defines legacy `invoices(id, customer_id, total_cents, created_at)`.
- `schema.sql` defines legacy `payments(id, invoice_id, amount_cents, created_at)` without a foreign key.
- The supplied seed contains 3 invoices and 4 payments.
- Payment `p4` references `missing-invoice`; it is the one orphan (1 of 4 payments).

## Required preservation

- All three invoice rows and their historical `created_at` values must survive.
- All valid payments (`p1`, `p2`, `p3`) remain in `payments`.
- `p4` must move, unchanged, to `payment_orphans` with a non-null reason; it must not be deleted.
- The rebuilt payments table must reject future references to nonexistent invoices.

## Execution gates

Run the migration against a copy of the database, inspect the postcheck results, and only then promote it. The migration uses `BEGIN IMMEDIATE` and commits its table rebuild atomically. `PRAGMA foreign_keys` is enabled for the migrated schema. Re-running the migration uses `INSERT OR IGNORE` for the orphan archive and does not duplicate rows.

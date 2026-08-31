# Billing migration report

## Changes applied
- Rebuilt `invoices` inside an explicit transaction to add `status TEXT NOT NULL DEFAULT 'open'`.
- Preserved invoice `id`, `customer_id`, `total_cents`, and historical `created_at` values.
- Preserved orphan payments by copying them into `payment_orphans` before rebuilding `payments`.
- Rebuilt `payments` so future `invoice_id` values must reference existing `invoices(id)`.
- Used `INSERT OR IGNORE` and stable primary keys so rerunning the migration does not duplicate `payment_orphans` rows or invoice/payment rows.

## Expected post-migration state for `schema.sql`
- `invoices`: 3 rows, each with `status = 'open'`
- `payments`: 3 rows referencing `inv1` or `inv2`
- `payment_orphans`: 1 row preserving `p4`
- `PRAGMA foreign_key_check`: no rows

## Rollback behavior
- Restores `invoices(id, customer_id, total_cents, created_at)`.
- Restores `payments(id, invoice_id, amount_cents, created_at)`.
- Moves preserved rows from `payment_orphans` back into `payments` before dropping `payment_orphans`.
- Leaves foreign-key enforcement off again to match the original package shape.

## Operator sequence
1. Review `preflight_report.md`.
2. Apply `migration.sql`.
3. Run `postcheck.sql`.
4. If reversal is required, run `rollback.sql` and re-check row counts and table shapes.

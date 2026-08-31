# Billing Migration Report

## Changes

- Rebuilt `invoices` with `status TEXT NOT NULL DEFAULT 'open'`.
- Copied every invoice without changing its historical `created_at`.
- Copied orphan payments to `payment_orphans` before rebuilding `payments`.
- Rebuilt `payments` with a foreign key from `invoice_id` to `invoices(id)`.
- Kept the migration inside an explicit transaction and restored foreign-key enforcement afterward.

## Safety

`p4` is preserved, not deleted. The migration is repeatable: preserved rows have primary-key conflict protection, and each temporary table is recreated from the current canonical data. `_billing_invoice_status` is an internal ledger used to retain status values during repeat rebuilds and is removed by rollback.

## Rollback

`rollback.sql` runs in its own transaction, removes `invoices.status`, removes the payments foreign key, restores rows from `payment_orphans` into `payments`, and drops the preservation tables. The resulting public columns are:

- `invoices(id, customer_id, total_cents, created_at)`
- `payments(id, invoice_id, amount_cents, created_at)`

## Verification

Run `postcheck.sql` after migration. It reports row counts, orphan preservation, status violations, historical timestamp violations, foreign-key violations, and the resulting table definitions.

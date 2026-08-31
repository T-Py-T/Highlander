# Billing Migration Report

## Changes

- Rebuilt `invoices` with `status TEXT NOT NULL DEFAULT 'open'`.
- Copied every invoice, including its original `created_at`.
- Copied valid payments and rebuilt `payments` with a foreign key to `invoices(id)`.
- Copied missing-invoice payments to `payment_orphans` with the original columns and a reason; no payment is deleted as historical data.
- Wrapped the complete migration in `BEGIN IMMEDIATE` / `COMMIT` and restored `PRAGMA foreign_keys = ON` after the transaction.

## Idempotency

`INSERT OR IGNORE` prevents duplicate orphan rows. `billing_invoice_status` preserves statuses across the table rebuild, so a second execution does not reset a changed status or duplicate data. Re-running the migration leaves the same invoice, payment, and orphan sets.

## Expected seed result

After migration: 3 invoices, 3 valid payments, and orphan `p4` in `payment_orphans`. All invoice statuses are `open`; invoice timestamps are unchanged.

## Rollback

Run `rollback.sql` only after a successful migration. It rebuilds both tables to their original four-column shapes, returns archived orphan rows (including `p4`) to `payments`, removes migration bookkeeping tables, and restores foreign-key enforcement.

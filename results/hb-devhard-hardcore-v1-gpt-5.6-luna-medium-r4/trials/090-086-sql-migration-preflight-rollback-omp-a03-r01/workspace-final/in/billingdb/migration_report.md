# Billing migration report

## Changes

- Added `invoices.status TEXT NOT NULL DEFAULT 'open'` while copying every
  invoice id, customer, total, and historical `created_at` unchanged.
- Copied payments whose invoice is missing into `payment_orphans` with the
  original four columns and reason `missing invoice`.
- Rebuilt `payments` with `REFERENCES invoices(id)` and retained only valid
  invoice references in that table; the invalid historical row remains in
  `payment_orphans`.
- Wrapped all table changes in `BEGIN IMMEDIATE` / `COMMIT`.
- Restored `PRAGMA foreign_keys = ON` after the table swaps.

## Idempotence

The migration uses deterministic table rebuilds, `IF EXISTS` cleanup for
staging tables, and `INSERT OR IGNORE` for the orphan archive. A second run
therefore retains the same invoice/payment rows and does not duplicate the
orphan archive.

## Rollback

`rollback.sql` rebuilds both tables to the legacy columns:

- `invoices(id, customer_id, total_cents, created_at)`
- `payments(id, invoice_id, amount_cents, created_at)`

It restores archived orphan rows to `payments`, including `p4`, and keeps
`payment_orphans` as an audit archive. It also runs in an explicit transaction
and restores foreign-key enforcement afterward. Keeping the archive makes the
rollback repeatable without losing the historical orphan record.

## Verification

Run `postcheck.sql` after migration. On the supplied seed, it should report
3 invoices, 3 valid payments, 1 archived orphan, `p4` preserved, all invoice
statuses `open`, zero invalid payment references, an empty `foreign_key_check`,
and `PRAGMA foreign_keys` equal to 1.

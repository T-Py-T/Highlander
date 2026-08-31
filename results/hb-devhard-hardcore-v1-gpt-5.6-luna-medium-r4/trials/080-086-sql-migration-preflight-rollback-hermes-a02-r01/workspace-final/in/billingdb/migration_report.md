# Billing migration report

## Changes made

- Added `invoices.status TEXT NOT NULL DEFAULT 'open'`.
- Copied all invoice legacy fields, including historical `created_at`.
- Copied valid payments unchanged.
- Moved orphan payments to `payment_orphans` before installing the payment FK.
- Rebuilt `payments` with `FOREIGN KEY (invoice_id) REFERENCES invoices(id)`.
- Kept foreign-key enforcement enabled and wrapped all migration changes in an
  explicit `BEGIN IMMEDIATE`/`COMMIT` transaction.

## Idempotence

The migration uses `IF NOT EXISTS`, `INSERT OR IGNORE`, and deterministic table
rebuilds. On a second run, existing invoice statuses are read from
`invoice_status`; a synchronization trigger preserves status changes made
between runs. Existing orphan rows are not duplicated, and payments are not
reinserted or deleted unexpectedly.

## Rollback

`rollback.sql` runs in its own explicit transaction, rebuilds `invoices` as
`(id, customer_id, total_cents, created_at)`, rebuilds `payments` as
`(id, invoice_id, amount_cents, created_at)` without a foreign key, restores
orphan rows from `payment_orphans`, and removes the migration's status map.
The `payment_orphans` audit table is intentionally retained.

## Verification

Run `postcheck.sql` after migration. With the supplied `schema.sql`, expected
results are 3 invoices, 3 valid payments, one preserved orphan (`p4`), zero
status nulls, zero changed invoice timestamps, zero FK violations, and
`foreign_keys_enabled = 1`.

# Billing Migration Report

## Changes

- Rebuilds `invoices` with `status TEXT NOT NULL DEFAULT 'open'` while
  copying every existing invoice and its original `created_at`.
- Copies invalid existing payments to `payment_orphans` before rebuilding
  `payments`; the orphan payload and a reason are retained.
- Rebuilds `payments` with a foreign key to `invoices`, so new invalid
  invoice IDs are rejected.
- Uses `BEGIN IMMEDIATE` and `COMMIT`; SQLite DDL in this file is therefore
  transactional.

## Rerun Safety

The orphan archive has a primary key and the archival insert checks it before
inserting. The rebuilt payments table contains only valid rows, so a second
run does not recreate or duplicate `p4` and produces the same row counts.

## Expected Results

After applying `schema.sql` and `migration.sql`, the expected counts are:

| Table | Rows |
| --- | ---: |
| `invoices` | 3 |
| `payments` | 3 |
| `payment_orphans` | 1 (`p4`) |

`postcheck.sql` should report foreign keys enabled, no invalid statuses, no
payments without invoices, and an empty `PRAGMA foreign_key_check` result.

## Rollback

Run `rollback.sql` only after the migration transaction has committed. It
restores `invoices(id, customer_id, total_cents, created_at)` and
`payments(id, invoice_id, amount_cents, created_at)`, moves archived payments
back into `payments`, removes the foreign key, and drops `payment_orphans`.

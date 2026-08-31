# Migration Report

## What Changed

- Replaced the unsafe draft migration with an explicit transaction.
- Added creation and population of `payment_orphans` for existing orphaned payments.
- Rebuilt `invoices` to add `status TEXT NOT NULL DEFAULT 'open'` while preserving `id`, `customer_id`, `total_cents`, and historical `created_at`.
- Rebuilt `payments` with a foreign-key reference to `invoices(id)` and copied only valid payments into the live table.

## Idempotency Notes

- `payment_orphans` uses `INSERT OR IGNORE` keyed by `id`, so reruns do not duplicate orphan records.
- The migration always rebuilds `invoices` and `payments` from the current live tables, so rerunning it after a successful migration does not duplicate rows.
- Temporary rebuild tables are dropped at the start of each run to avoid collisions from partial or interrupted attempts.

## Rollback Behavior

- `rollback.sql` restores the old table shapes:
  - `invoices(id, customer_id, total_cents, created_at)`
  - `payments(id, invoice_id, amount_cents, created_at)`
- Rollback reinserts preserved orphan payments from `payment_orphans` back into `payments` while keeping `payment_orphans` intact.

## Postchecks

- `postcheck.sql` validates row counts, orphan preservation, non-null default invoice status, and foreign-key integrity.

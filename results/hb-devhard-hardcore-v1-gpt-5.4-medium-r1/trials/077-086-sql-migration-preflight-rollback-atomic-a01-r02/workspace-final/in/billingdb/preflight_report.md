# Billing migration preflight report

## Source tables
- `invoices`: 3 rows
- `payments`: 4 rows

## Orphan payments found
- 1 orphan payment
- row: `p4 | missing-invoice | 700 | 2024-01-07T10:00:00Z`

## Risks in the draft migration
- Dropped orphan payments instead of preserving them.
- Rebuilt `invoices` without an explicit transaction.
- Did not add a rollback script.
- Did not add post-migration checks.
- Did not enforce future `payments.invoice_id` safety with a foreign key.

## Expected migration result
- `invoices` keeps all 3 rows and gains `status TEXT NOT NULL DEFAULT 'open'`.
- `payments` keeps valid rows `p1`, `p2`, `p3`.
- orphan payment `p4` moves to `payment_orphans` with a reason.
- future `payments.invoice_id` values must match a real invoice.

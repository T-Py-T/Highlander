# Billing migration preflight report

## Source snapshot
- `invoices` rows: 3
- `payments` rows: 4
- orphan payments: 1

## Orphan payment detail
| id | invoice_id | amount_cents | created_at | note |
| --- | --- | ---: | --- | --- |
| p4 | missing-invoice | 700 | 2024-01-07T10:00:00Z | keep and move to `payment_orphans` |

## Migration plan
1. Run inside one explicit transaction.
2. Create `payment_orphans` if needed.
3. Copy orphan payments into `payment_orphans` with reason `missing_invoice`.
4. Remove moved orphan rows from `payments` before adding referential safety.
5. Rebuild `invoices` with `status TEXT NOT NULL DEFAULT 'open'`.
6. Rebuild `payments` with a foreign key to `invoices(id)`.
7. Restore `PRAGMA foreign_keys = ON` and commit.

## Expected post-migration state
- `invoices` rows stay at 3.
- `payments` rows become 3.
- `payment_orphans` rows become 1.
- all invoice `created_at` values stay unchanged.
- all migrated invoice `status` values are `open`.
- `payments.invoice_id` points only to real invoices.

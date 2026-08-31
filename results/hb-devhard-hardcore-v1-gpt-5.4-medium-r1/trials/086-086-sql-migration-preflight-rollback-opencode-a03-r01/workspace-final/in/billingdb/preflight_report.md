# Preflight Report

Source dataset from `schema.sql`:

- `invoices`: 3 rows (`inv1`, `inv2`, `inv3`)
- `payments`: 4 rows (`p1`, `p2`, `p3`, `p4`)
- orphan payments: 1 row

Detected orphan payment to preserve before referential enforcement:

| payment_id | invoice_id | amount_cents | created_at | reason |
| --- | --- | ---: | --- | --- |
| `p4` | `missing-invoice` | 700 | `2024-01-07T10:00:00Z` | missing parent invoice |

Migration expectations:

- preserve all invoice rows and their original `created_at` values
- add `invoices.status TEXT NOT NULL DEFAULT 'open'`
- preserve `p4` by moving it to `payment_orphans`
- rebuild `payments` so every remaining `invoice_id` references a real invoice
- run inside an explicit transaction and support safe repeat execution

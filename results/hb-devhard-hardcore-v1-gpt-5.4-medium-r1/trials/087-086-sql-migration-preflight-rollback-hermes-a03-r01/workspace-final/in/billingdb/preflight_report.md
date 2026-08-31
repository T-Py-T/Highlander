# Billing migration preflight report

Source inspected: `schema.sql`

## Baseline row counts

- invoices: 3
- payments: 4
- orphan payments: 1

## Orphan payment inventory

| id | invoice_id | amount_cents | created_at | reason |
| --- | --- | ---: | --- | --- |
| p4 | missing-invoice | 700 | 2024-01-07T10:00:00Z | references no row in `invoices` |

## Required migration actions

1. Preserve all 3 invoices.
2. Preserve all valid payments (`p1`, `p2`, `p3`) in `payments`.
3. Move orphan payment `p4` into `payment_orphans` without changing its business fields.
4. Add `invoices.status TEXT NOT NULL DEFAULT 'open'` while preserving historical `created_at` values.
5. Rebuild `payments` with a foreign key to `invoices(id)` so future bad references fail.
6. Run everything inside an explicit transaction and make reruns safe.

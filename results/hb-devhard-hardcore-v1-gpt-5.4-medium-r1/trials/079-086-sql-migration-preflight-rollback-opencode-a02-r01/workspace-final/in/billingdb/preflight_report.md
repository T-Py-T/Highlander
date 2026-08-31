# Preflight Report

## Baseline Counts

| Table | Row count |
| --- | ---: |
| invoices | 3 |
| payments | 4 |

## Orphan Payments Detected

| Payment id | invoice_id | amount_cents | created_at | Reason |
| --- | --- | ---: | --- | --- |
| p4 | missing-invoice | 700 | 2024-01-07T10:00:00Z | No matching `invoices.id` exists in the baseline schema. |

## Migration Actions

- Preserve all invoice rows and keep each original `created_at` value.
- Add `invoices.status TEXT NOT NULL DEFAULT 'open'`.
- Copy orphan payments into `payment_orphans` before rebuilding `payments` with a foreign key.
- Rebuild `payments` so future `invoice_id` values must reference a valid invoice.
- Run the migration inside an explicit transaction and restore `PRAGMA foreign_keys = ON` afterward.

# Billing Migration Preflight Report

## Source snapshot
- invoices rows: 3
- payments rows: 4
- orphan payments detected before migration: 1

## Orphan payments
| id | invoice_id | amount_cents | created_at | reason |
| --- | --- | ---: | --- | --- |
| p4 | missing-invoice | 700 | 2024-01-07T10:00:00Z | Missing parent invoice in legacy import data |

## Planned migration effects
- Add `invoices.status TEXT NOT NULL DEFAULT 'open'`.
- Preserve all invoice rows and their original `created_at` values.
- Move existing orphan payments into `payment_orphans` before rebuilding `payments` with a foreign key to `invoices(id)`.
- Preserve valid payment rows in `payments` without rewriting timestamps.
- Run the migration in an explicit transaction and make repeated execution safe through `INSERT OR IGNORE` plus full-table rebuilds.

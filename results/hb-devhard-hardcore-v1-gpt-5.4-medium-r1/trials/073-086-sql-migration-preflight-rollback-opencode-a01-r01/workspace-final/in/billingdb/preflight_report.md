# Preflight Report

## Source Summary

- `invoices` rows: 3
- `payments` rows: 4
- orphan payments detected: 1

## Orphan Payments

| id | invoice_id | amount_cents | created_at | issue |
| --- | --- | ---: | --- | --- |
| `p4` | `missing-invoice` | 700 | `2024-01-07T10:00:00Z` | invoice does not exist in `invoices` |

## Migration Actions

- rebuild `invoices` to add `status TEXT NOT NULL DEFAULT 'open'`
- preserve every invoice row and original `created_at`
- move orphan payments into `payment_orphans` before enforcing foreign keys on `payments`
- rebuild `payments` with a foreign key to `invoices(id)` for future referential safety
- execute the migration inside an explicit transaction
- support safe reruns without duplicating invoice, payment, or orphan rows

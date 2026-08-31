# Billing migration preflight report

## Source
- `in/billingdb/schema.sql`

## Current row counts before migration
- `invoices`: 3
- `payments`: 4
- orphan payments: 1

## Orphan payments found
| id | invoice_id | amount_cents | created_at |
| --- | --- | ---: | --- |
| `p4` | `missing-invoice` | 700 | `2024-01-07T10:00:00Z` |

## Risks in the draft migration
- It drops and recreates `invoices` without an explicit transaction.
- It deletes orphan payments instead of preserving them.
- It does not create `payment_orphans`.
- It does not enforce future `payments.invoice_id` references with a foreign key.
- It is not safe to rerun as written.

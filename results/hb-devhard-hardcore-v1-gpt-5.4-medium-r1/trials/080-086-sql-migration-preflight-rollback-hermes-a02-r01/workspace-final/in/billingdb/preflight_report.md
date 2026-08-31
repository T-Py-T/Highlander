# Billing migration preflight report

Source inspected: `schema.sql`

## Current row counts before migration
- `invoices`: 3
- `payments`: 4
- orphan payments in `payments`: 1

## Orphan payments detected
| payment_id | invoice_id | amount_cents | created_at | issue |
| --- | --- | ---: | --- | --- |
| `p4` | `missing-invoice` | 700 | `2024-01-07T10:00:00Z` | invoice does not exist in `invoices` |

## Preflight conclusions
- Adding `invoices.status TEXT NOT NULL DEFAULT 'open'` requires rebuilding `invoices` so all historical rows gain a non-null status without changing `created_at`.
- Existing orphan payment `p4` must be preserved by copying it into `payment_orphans` before referential enforcement is applied to `payments`.
- After migration, `payments.invoice_id` must only contain valid invoice references and foreign key enforcement must be enabled again.
- The migration should run inside one explicit transaction and be safe to run a second time without duplicating preserved orphan records.

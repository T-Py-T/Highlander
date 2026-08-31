# Preflight Report

Source inspected: `schema.sql`

## Baseline row counts
- invoices: 3
- payments: 4
- orphan payments: 1

## Orphan payments detected
| id | invoice_id | amount_cents | created_at |
| --- | --- | ---: | --- |
| p4 | missing-invoice | 700 | 2024-01-07T10:00:00Z |

## Invoice history to preserve
| invoice_id | created_at |
| --- | --- |
| inv1 | 2024-01-03T10:00:00Z |
| inv2 | 2024-01-04T10:00:00Z |
| inv3 | 2024-01-05T10:00:00Z |

## Migration requirements covered
- Add `invoices.status TEXT NOT NULL DEFAULT 'open'`.
- Preserve all invoices from the baseline dataset.
- Preserve valid payments in `payments`.
- Move orphan payment `p4` into `payment_orphans` instead of deleting it.
- Enforce future `payments.invoice_id` references with a foreign key.
- Run the migration inside an explicit transaction.
- Provide rollback SQL that restores the original table shapes.
- Provide post-migration checks for counts, defaults, orphan preservation, and foreign-key integrity.

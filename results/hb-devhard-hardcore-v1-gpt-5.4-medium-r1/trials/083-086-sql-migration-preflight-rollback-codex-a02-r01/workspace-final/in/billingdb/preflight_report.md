# Billing Migration Preflight Report

Date: 2026-08-31

## Source Snapshot

From `schema.sql`:

- `invoices` rows: 3
- `payments` rows: 4
- orphan payments detected before migration: 1

## Orphan Payments

The following payment does not reference an existing invoice and must be preserved outside the constrained `payments` table before a foreign key is enforced:

| id | invoice_id | amount_cents | created_at |
| --- | --- | ---: | --- |
| `p4` | `missing-invoice` | 700 | `2024-01-07T10:00:00Z` |

## Migration Requirements Applied

- Add `invoices.status TEXT NOT NULL DEFAULT 'open'`.
- Preserve all invoice and payment rows from the legacy schema.
- Preserve invoice `created_at` values exactly.
- Move orphan payments into `payment_orphans` before rebuilding `payments`.
- Enforce valid future `payments.invoice_id` references with a foreign key.
- Run the migration inside an explicit transaction.
- Keep reruns safe by using deterministic table rebuilds and `INSERT OR IGNORE` for orphan preservation.

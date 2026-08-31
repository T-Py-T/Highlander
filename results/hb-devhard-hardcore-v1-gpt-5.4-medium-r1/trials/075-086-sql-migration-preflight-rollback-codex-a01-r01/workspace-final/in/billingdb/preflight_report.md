# Billing Migration Preflight Report

## Source baseline

- Source file: `schema.sql`
- Invoice rows: `3`
- Payment rows: `4`
- Expected valid payments after referential cleanup: `3`
- Expected orphan payments to preserve in `payment_orphans`: `1`

## Orphan payments detected

| id | invoice_id | amount_cents | created_at | issue |
| --- | --- | ---: | --- | --- |
| `p4` | `missing-invoice` | `700` | `2024-01-07T10:00:00Z` | references no invoice in `invoices` |

## Migration requirements covered

- Add `invoices.status TEXT NOT NULL DEFAULT 'open'`.
- Preserve all invoice rows and original `created_at` values.
- Move orphan payments into `payment_orphans` before enforcing payment referential safety.
- Rebuild `payments` with a foreign key so future `invoice_id` values must reference a valid invoice.
- Execute inside an explicit transaction and restore `PRAGMA foreign_keys = ON` after the migration.
- Make reruns safe by using stable backup tables plus `INSERT OR IGNORE` for orphan preservation.

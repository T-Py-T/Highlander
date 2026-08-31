# Migration Report

Updated package contents:

- `migration.sql`: replaced the unsafe draft with a transaction-safe SQLite rebuild migration
- `preflight_report.md`: documented source row counts and the orphan payment that must be preserved
- `rollback.sql`: restores the legacy `invoices` and `payments` table shapes and puts orphan rows back into `payments`
- `postcheck.sql`: validates row counts, `status` backfill/default metadata, orphan preservation, and foreign-key integrity

Migration behavior:

- preserves all invoice rows and historical `created_at` values
- adds `invoices.status TEXT NOT NULL DEFAULT 'open'`
- copies orphan payments such as `p4` into `payment_orphans` before rebuilding `payments`
- rebuilds `payments` with a live foreign-key reference to `invoices(id)` so future inserts must target valid invoices
- supports repeat execution without duplicating payments or orphan rows

Rollback behavior:

- restores `invoices(id, customer_id, total_cents, created_at)`
- restores `payments(id, invoice_id, amount_cents, created_at)`
- reinserts preserved orphan payments from `payment_orphans` back into `payments`
- removes migration helper objects created for idempotent status preservation

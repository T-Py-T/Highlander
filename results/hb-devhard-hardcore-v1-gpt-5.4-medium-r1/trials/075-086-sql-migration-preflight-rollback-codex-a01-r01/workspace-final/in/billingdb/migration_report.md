# Billing Migration Repair Report

## Problems in the original draft

- It dropped and recreated `invoices` outside an explicit transaction.
- It deleted orphan payments instead of preserving them.
- It did not create `payment_orphans`.
- It did not enforce future referential safety on `payments.invoice_id`.
- It was not safe to rerun because it relied on one-time destructive table replacement.

## Repair implemented

- Added an explicit `BEGIN IMMEDIATE ... COMMIT` transaction.
- Restored `PRAGMA foreign_keys = ON` after the migration.
- Added stable backup tables to make the migration rerunnable without duplicating invoices, payments, or orphan rows.
- Added `payment_orphans(id, invoice_id, amount_cents, created_at, reason)` and moved orphaned legacy payments there with `INSERT OR IGNORE`.
- Rebuilt `invoices` with `status TEXT NOT NULL DEFAULT 'open'`.
- Rebuilt `payments` so `invoice_id` has a foreign key to `invoices(id)`.
- Preserved all invoice `created_at` values and all valid legacy payments.
- Preserved orphan payment `p4` in `payment_orphans` instead of deleting it.

## Package contents

- `migration.sql`: transaction-safe, idempotent migration.
- `preflight_report.md`: baseline counts and orphan inventory from `schema.sql`.
- `rollback.sql`: restores the old `invoices` and `payments` column shape after migration.
- `postcheck.sql`: verifies row counts, status column/defaults, orphan preservation, created-at preservation, and foreign-key integrity.

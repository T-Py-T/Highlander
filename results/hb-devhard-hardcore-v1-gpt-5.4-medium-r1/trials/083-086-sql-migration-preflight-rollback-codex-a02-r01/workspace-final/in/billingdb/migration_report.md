# Billing Migration Report

Date: 2026-08-31

## Deliverables

- `migration.sql`: transactional, idempotent table rebuild migration.
- `rollback.sql`: restores the legacy `invoices` and `payments` table shapes and merges preserved orphan payments back into `payments`.
- `postcheck.sql`: verifies row counts, `status` defaults, orphan preservation, invalid payment references, and foreign key integrity.
- `preflight_report.md`: captures the starting row counts and orphan payment inventory from `schema.sql`.

## Migration Behavior

`migration.sql` performs the following:

1. Starts an explicit transaction with foreign-key enforcement restored after commit.
2. Creates `payment_orphans` if needed.
3. Copies legacy orphan payments into `payment_orphans` with reason `missing invoice during migration`.
4. Rebuilds `invoices` to add `status TEXT NOT NULL DEFAULT 'open'` while preserving all legacy invoice data, including historical `created_at`.
5. Rebuilds `payments` with a foreign key to `invoices`, copying only rows that reference valid invoices.

## Rollback Behavior

`rollback.sql`:

1. Rebuilds `invoices` back to `id, customer_id, total_cents, created_at`.
2. Rebuilds `payments` back to `id, invoice_id, amount_cents, created_at`.
3. Reinserts preserved rows from `payment_orphans` so legacy orphan payment `p4` returns to `payments`.
4. Drops `payment_orphans` to restore the legacy schema footprint.

## Expected Post-Migration State For The Provided Seed Data

- `invoices`: 3 rows
- `payments`: 3 rows
- `payment_orphans`: 1 row
- `payment_orphans` contains `p4`
- `payments` contains no invalid `invoice_id` references

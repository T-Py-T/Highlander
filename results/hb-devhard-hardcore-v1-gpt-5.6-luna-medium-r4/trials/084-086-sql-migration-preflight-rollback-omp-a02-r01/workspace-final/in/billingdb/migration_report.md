# Billing migration report

## Changes

`migration.sql` runs an explicit `BEGIN IMMEDIATE` transaction. It first renames the source payments table, archives every payment whose invoice is absent, rebuilds invoices with `status TEXT NOT NULL DEFAULT 'open'`, then rebuilds payments with `FOREIGN KEY (invoice_id) REFERENCES invoices(id)`. Invoice identifiers, customer IDs, totals, and historical creation timestamps are copied. Archived orphan values are copied unchanged and receive a reason.

The rebuild is repeatable: staging tables are removed before use, valid rows are copied by primary key, and orphan archival uses `INSERT OR IGNORE`. A second run therefore leaves three valid payments and one `p4` archive for the supplied seed rather than creating duplicates.

## Rollback

`rollback.sql` temporarily disables foreign-key enforcement only while replacing the migrated tables, inside its transaction, and restores `PRAGMA foreign_keys = ON` before completion. It removes `status`, recreates the legacy table definitions, and restores archived payments—including `p4`—to `payments`. The auxiliary `payment_orphans` table is then dropped because the legacy schema has no quarantine table.

## Post-migration acceptance

`postcheck.sql` reports foreign-key mode, row counts, `p4` preservation, status metadata/defaults, invalid references, `PRAGMA foreign_key_check`, and invoice timestamps. With the supplied seed, expected counts are invoices=3, payments=3, payment_orphans=1, and all invoice statuses=`open`.

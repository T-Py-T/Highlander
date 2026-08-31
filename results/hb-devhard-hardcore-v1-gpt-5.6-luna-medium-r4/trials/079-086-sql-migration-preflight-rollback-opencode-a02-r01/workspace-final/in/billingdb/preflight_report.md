# Billing Migration Preflight

Source: `schema.sql`.

## Inventory

- Invoices: 3 (`inv1`, `inv2`, `inv3`)
- Payments: 4 (`p1`, `p2`, `p3`, `p4`)
- Orphan payments: 1 (`p4`), referencing `missing-invoice`, amount `700`, created `2024-01-07T10:00:00Z`

The migration preserves all invoice rows and all payment values. The three valid payments remain in `payments`; `p4` is copied unchanged to `payment_orphans` with a non-null explanatory `reason` before the new foreign key is enforced.

## Required Checks

Run these queries against a copy of the database before migration:

```sql
SELECT COUNT(*) FROM invoices;
SELECT COUNT(*) FROM payments;
SELECT p.* FROM payments AS p LEFT JOIN invoices AS i ON i.id = p.invoice_id WHERE i.id IS NULL;
```

The migration is transaction-scoped and restores `PRAGMA foreign_keys` to `ON`. Its rebuild can be run repeatedly: primary-key inserts into the preservation tables are `INSERT OR IGNORE`, and temporary rebuild tables are dropped before recreation.

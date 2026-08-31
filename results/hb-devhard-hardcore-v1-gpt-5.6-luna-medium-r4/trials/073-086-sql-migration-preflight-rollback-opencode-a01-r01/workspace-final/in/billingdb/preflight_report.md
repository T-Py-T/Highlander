# Billing Migration Preflight

## Source snapshot

The supplied `schema.sql` contains:

- `invoices`: 3 rows (`inv1`, `inv2`, `inv3`)
- `payments`: 4 rows (`p1`, `p2`, `p3`, `p4`)
- orphan payments: 1 (`p4`, referencing `missing-invoice`, amount 700)

`p4` is a historical import issue and must be copied to `payment_orphans`, not deleted.

## Preconditions

Run the following checks against the target database before applying `migration.sql`:

```sql
SELECT COUNT(*) AS invoice_count FROM invoices;
SELECT COUNT(*) AS payment_count FROM payments;
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;
PRAGMA foreign_keys;
```

The migration takes an immediate write lock, keeps all DDL and data movement in one explicit transaction, preserves invoice timestamps, archives orphans, and enables foreign-key enforcement after commit.

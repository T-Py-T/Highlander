# Billing migration preflight

## Scope

The migration rebuilds `invoices` with a non-null `status` column and rebuilds
`payments` with a foreign key to `invoices(id)`. SQLite foreign-key enforcement
is disabled only during the table swaps and is explicitly enabled again after
the transaction. Existing invalid payment references are copied first to
`payment_orphans`; they are never deleted.

## Seed inventory

| Check | Expected |
|---|---:|
| invoices before migration | 3 |
| payments before migration | 4 |
| payments referencing a missing invoice | 1 |
| orphan identifier | `p4` |
| orphan invoice reference | `missing-invoice` |

The orphan row is `p4`, amount `700`, created at
`2024-01-07T10:00:00Z`. It must remain in `payment_orphans`.

## Run before migration

```sql
SELECT COUNT(*) AS invoice_count FROM invoices;
SELECT COUNT(*) AS payment_count FROM payments;
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;
```

The migration is safe to proceed when the orphan list is reviewed and the
counts match the inventory above (or are otherwise explicitly approved).
`postcheck.sql` contains the after-migration assertions.

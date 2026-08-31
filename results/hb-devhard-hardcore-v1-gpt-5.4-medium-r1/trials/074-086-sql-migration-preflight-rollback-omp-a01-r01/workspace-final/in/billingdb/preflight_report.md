# Billing migration preflight report

## Scope
- Source tables: `invoices`, `payments`
- Target additions: `invoices.status`, `payment_orphans`, foreign-key-safe `payments`

## Preflight SQL
```sql
SELECT 'invoice_count' AS metric, COUNT(*) AS value FROM invoices;
SELECT 'payment_count' AS metric, COUNT(*) AS value FROM payments;
SELECT 'orphan_payment_count' AS metric, COUNT(*) AS value
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;

SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL
ORDER BY p.id;
```

## Observed result from `schema.sql`
- `invoices`: 3 rows
- `payments`: 4 rows
- orphan payments: 1 row
- orphan detail preserved by migration: `p4 | missing-invoice | 700 | 2024-01-07T10:00:00Z`

## Migration gate
- Do not proceed unless the orphan set is understood and intentionally moved into `payment_orphans`.
- Do not proceed unless the migration is run as a single explicit transaction.
- Do not proceed unless postcheck and rollback scripts are available beside the migration.

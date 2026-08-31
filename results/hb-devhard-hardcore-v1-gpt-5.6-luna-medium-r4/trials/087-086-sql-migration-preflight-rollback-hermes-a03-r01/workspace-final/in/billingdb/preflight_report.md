# Billing migration preflight report

Source: `schema.sql` (the supplied fixture).

## Findings

| Check | Result |
|---|---:|
| Invoice rows | 3 |
| Payment rows | 4 |
| Payments with a matching invoice | 3 |
| Orphan payments | 1 |
| Invoice IDs | `inv1`, `inv2`, `inv3` |

The orphan is:

| id | invoice_id | amount_cents | created_at | migration action |
|---|---|---:|---|---|
| `p4` | `missing-invoice` | 700 | `2024-01-07T10:00:00Z` | Move unchanged to `payment_orphans`; do not delete |

## Safety decision

Proceed only with a transaction-wrapped table rebuild. The migration first copies every orphan to `payment_orphans`, then installs a foreign key on the replacement `payments` table. Valid invoice and payment rows are copied without changing their IDs, amounts, or timestamps. Invoice `created_at` is copied from the old table and `status` is added as `TEXT NOT NULL DEFAULT 'open'`.

The migration ends with `PRAGMA foreign_keys = ON`. No source rows are deleted as a data-cleanup shortcut; the only deletes are table replacements after their contents have been copied.

## Reproducible preflight queries

```sql
SELECT COUNT(*) AS invoice_count FROM invoices;
SELECT COUNT(*) AS payment_count FROM payments;
SELECT COUNT(*) AS orphan_count
FROM payments AS p
WHERE NOT EXISTS (SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id);
SELECT p.*
FROM payments AS p
WHERE NOT EXISTS (SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id)
ORDER BY p.id;
```

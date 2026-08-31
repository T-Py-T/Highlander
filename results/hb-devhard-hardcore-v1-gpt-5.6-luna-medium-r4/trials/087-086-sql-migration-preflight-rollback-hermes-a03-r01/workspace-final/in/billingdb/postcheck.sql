-- Run after migration.sql. These queries are intentionally plain SQLite.

SELECT 'invoices' AS object, COUNT(*) AS row_count FROM invoices
UNION ALL
SELECT 'payments', COUNT(*) FROM payments
UNION ALL
SELECT 'payment_orphans', COUNT(*) FROM payment_orphans;

SELECT id, customer_id, total_cents, created_at, status
FROM invoices
ORDER BY id;

-- Required: every migrated invoice has a non-null open status in this fixture.
SELECT COUNT(*) AS invoices_with_null_status
FROM invoices
WHERE status IS NULL;
SELECT COUNT(*) AS invoices_with_open_default
FROM invoices
WHERE status = 'open';

-- p4 must be preserved in the orphan archive, unchanged.
SELECT id, invoice_id, amount_cents, created_at, reason
FROM payment_orphans
ORDER BY id;
SELECT COUNT(*) AS preserved_p4
FROM payment_orphans
WHERE id = 'p4'
  AND invoice_id = 'missing-invoice'
  AND amount_cents = 700
  AND created_at = '2024-01-07T10:00:00Z';

-- This must return zero. The FK itself is reported by the next statements.
SELECT COUNT(*) AS payments_without_valid_invoice
FROM payments AS p
WHERE NOT EXISTS (SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id);
PRAGMA foreign_key_list(payments);
PRAGMA foreign_key_check;

-- Historical timestamps must remain unchanged.
SELECT COUNT(*) AS unexpected_invoice_timestamps
FROM invoices
WHERE (id = 'inv1' AND created_at <> '2024-01-03T10:00:00Z')
   OR (id = 'inv2' AND created_at <> '2024-01-04T10:00:00Z')
   OR (id = 'inv3' AND created_at <> '2024-01-05T10:00:00Z');

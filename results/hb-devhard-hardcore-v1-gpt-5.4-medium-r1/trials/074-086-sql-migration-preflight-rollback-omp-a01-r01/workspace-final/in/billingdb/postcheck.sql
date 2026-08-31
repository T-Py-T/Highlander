PRAGMA foreign_keys = ON;

SELECT 'invoice_count' AS check_name, COUNT(*) AS value FROM invoices;
SELECT 'payment_count' AS check_name, COUNT(*) AS value FROM payments;
SELECT 'payment_orphan_count' AS check_name, COUNT(*) AS value FROM payment_orphans;
SELECT 'null_status_count' AS check_name, COUNT(*) AS value FROM invoices WHERE status IS NULL;
SELECT 'non_open_status_count' AS check_name, COUNT(*) AS value FROM invoices WHERE status <> 'open';
SELECT 'preserved_invoice_created_at_count' AS check_name, COUNT(*) AS value
FROM invoices
WHERE (id, created_at) IN (
  ('inv1', '2024-01-03T10:00:00Z'),
  ('inv2', '2024-01-04T10:00:00Z'),
  ('inv3', '2024-01-05T10:00:00Z')
);
SELECT 'preserved_orphan_p4_count' AS check_name, COUNT(*) AS value
FROM payment_orphans
WHERE id = 'p4'
  AND invoice_id = 'missing-invoice'
  AND amount_cents = 700
  AND created_at = '2024-01-07T10:00:00Z';
SELECT 'dangling_payment_count' AS check_name, COUNT(*) AS value
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;
PRAGMA foreign_key_check;

SELECT 'invoice_count' AS check_name, COUNT(*) AS value
FROM invoices;

SELECT 'invoice_status_open_count' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status = 'open';

SELECT 'invoice_status_null_count' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status IS NULL;

SELECT 'payment_count' AS check_name, COUNT(*) AS value
FROM payments;

SELECT 'payment_orphan_count' AS check_name, COUNT(*) AS value
FROM payment_orphans;

SELECT 'preserved_orphan_p4' AS check_name, COUNT(*) AS value
FROM payment_orphans
WHERE id = 'p4'
  AND invoice_id = 'missing-invoice'
  AND amount_cents = 700
  AND created_at = '2024-01-07T10:00:00Z';

SELECT 'preserved_invoice_created_at' AS check_name, COUNT(*) AS value
FROM invoices
WHERE (id = 'inv1' AND created_at = '2024-01-03T10:00:00Z')
   OR (id = 'inv2' AND created_at = '2024-01-04T10:00:00Z')
   OR (id = 'inv3' AND created_at = '2024-01-05T10:00:00Z');

SELECT 'remaining_invalid_payment_refs' AS check_name, COUNT(*) AS value
FROM payments AS p
LEFT JOIN invoices AS i
  ON i.id = p.invoice_id
WHERE i.id IS NULL;

PRAGMA foreign_key_check;

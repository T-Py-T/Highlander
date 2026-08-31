PRAGMA foreign_keys = ON;

SELECT 'invoices_count' AS check_name, COUNT(*) AS value
FROM invoices;

SELECT 'payments_count' AS check_name, COUNT(*) AS value
FROM payments;

SELECT 'payment_orphans_count' AS check_name, COUNT(*) AS value
FROM payment_orphans;

SELECT 'invoice_status_nulls' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status IS NULL;

SELECT 'invoice_status_non_open' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status <> 'open';

SELECT 'preserved_p4' AS check_name, COUNT(*) AS value
FROM payment_orphans
WHERE id = 'p4'
  AND invoice_id = 'missing-invoice'
  AND amount_cents = 700
  AND created_at = '2024-01-07T10:00:00Z';

SELECT 'payments_with_missing_invoice' AS check_name, COUNT(*) AS value
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;

SELECT 'created_at_changed' AS check_name, COUNT(*) AS value
FROM invoices
WHERE (id = 'inv1' AND created_at <> '2024-01-03T10:00:00Z')
   OR (id = 'inv2' AND created_at <> '2024-01-04T10:00:00Z')
   OR (id = 'inv3' AND created_at <> '2024-01-05T10:00:00Z');

PRAGMA foreign_key_check;

PRAGMA foreign_keys = ON;

SELECT 'invoices_row_count' AS check_name, COUNT(*) AS value
FROM invoices;

SELECT 'payments_row_count' AS check_name, COUNT(*) AS value
FROM payments;

SELECT 'payment_orphans_row_count' AS check_name, COUNT(*) AS value
FROM payment_orphans;

SELECT 'invalid_payment_refs' AS check_name, COUNT(*) AS value
FROM payments AS p
LEFT JOIN invoices AS i
  ON i.id = p.invoice_id
WHERE i.id IS NULL;

SELECT 'null_invoice_status_count' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status IS NULL;

SELECT 'open_invoice_status_count' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status = 'open';

SELECT 'preserved_p4_in_payment_orphans' AS check_name, COUNT(*) AS value
FROM payment_orphans
WHERE id = 'p4'
  AND invoice_id = 'missing-invoice'
  AND amount_cents = 700
  AND created_at = '2024-01-07T10:00:00Z';

PRAGMA foreign_key_check;

SELECT 'invoices_count' AS check_name, COUNT(*) AS value
FROM invoices;

SELECT 'payments_count' AS check_name, COUNT(*) AS value
FROM payments;

SELECT 'payment_orphans_count' AS check_name, COUNT(*) AS value
FROM payment_orphans;

SELECT 'orphan_p4_preserved' AS check_name,
       EXISTS(SELECT 1 FROM payment_orphans WHERE id = 'p4' AND invoice_id = 'missing-invoice' AND amount_cents = 700 AND created_at = '2024-01-07T10:00:00Z') AS value;

SELECT 'invoice_status_null_count' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status IS NULL;

SELECT 'invoice_status_open_count' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status = 'open';

SELECT 'invalid_payment_references' AS check_name, COUNT(*) AS value
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;

PRAGMA foreign_key_check;

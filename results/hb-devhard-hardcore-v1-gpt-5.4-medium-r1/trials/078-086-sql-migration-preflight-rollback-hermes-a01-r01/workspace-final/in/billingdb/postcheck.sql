SELECT 'invoices_count' AS check_name, COUNT(*) AS value FROM invoices;
SELECT 'payments_count' AS check_name, COUNT(*) AS value FROM payments;
SELECT 'payment_orphans_count' AS check_name, COUNT(*) AS value FROM payment_orphans;
SELECT 'invoice_status_null_count' AS check_name, COUNT(*) AS value FROM invoices WHERE status IS NULL;
SELECT 'invoice_status_non_open_count' AS check_name, COUNT(*) AS value FROM invoices WHERE status <> 'open';
SELECT 'preserved_orphan_p4_count' AS check_name, COUNT(*) AS value FROM payment_orphans WHERE id = 'p4' AND invoice_id = 'missing-invoice';
SELECT 'invalid_payment_reference_count' AS check_name, COUNT(*) AS value
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;
PRAGMA foreign_key_check;

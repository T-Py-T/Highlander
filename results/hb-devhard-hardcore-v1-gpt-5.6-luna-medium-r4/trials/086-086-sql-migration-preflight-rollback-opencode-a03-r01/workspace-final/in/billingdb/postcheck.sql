-- Diagnostic post-migration checks. Empty foreign_key_check output is required.
SELECT 'invoices' AS check_name, COUNT(*) AS value FROM invoices;
SELECT 'payments' AS check_name, COUNT(*) AS value FROM payments;
SELECT 'payment_orphans' AS check_name, COUNT(*) AS value FROM payment_orphans;
SELECT 'null_or_invalid_status' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status IS NULL OR status <> 'open';
SELECT 'payments_without_invoice' AS check_name, COUNT(*) AS value
FROM payments AS p
WHERE NOT EXISTS (SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id);
SELECT 'p4_archived' AS check_name, COUNT(*) AS value
FROM payment_orphans
WHERE id = 'p4' AND invoice_id = 'missing-invoice'
  AND amount_cents = 700 AND created_at = '2024-01-07T10:00:00Z';
SELECT 'foreign_keys' AS check_name, foreign_keys AS value FROM pragma_foreign_keys;
SELECT 'foreign_key_list_payments' AS check_name, COUNT(*) AS value
FROM pragma_foreign_key_list('payments');
PRAGMA foreign_key_check;

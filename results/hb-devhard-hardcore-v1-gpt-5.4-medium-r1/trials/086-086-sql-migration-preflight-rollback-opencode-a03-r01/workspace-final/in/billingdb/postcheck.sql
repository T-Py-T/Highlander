SELECT 'invoice_row_count' AS check_name, COUNT(*) AS value
FROM invoices;

SELECT 'payment_row_count' AS check_name, COUNT(*) AS value
FROM payments;

SELECT 'payment_orphan_row_count' AS check_name, COUNT(*) AS value
FROM payment_orphans;

SELECT 'invoice_status_column_present' AS check_name,
       COUNT(*) AS value
FROM pragma_table_info('invoices')
WHERE name = 'status'
  AND type = 'TEXT'
  AND "notnull" = 1
  AND dflt_value = '''open''';

SELECT 'null_invoice_status_count' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status IS NULL;

SELECT 'open_invoice_status_count' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status = 'open';

SELECT 'preserved_orphan_p4' AS check_name, COUNT(*) AS value
FROM payment_orphans
WHERE id = 'p4'
  AND invoice_id = 'missing-invoice'
  AND amount_cents = 700
  AND created_at = '2024-01-07T10:00:00Z'
  AND reason = 'missing_invoice';

SELECT 'invalid_payment_invoice_refs' AS check_name, COUNT(*) AS value
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;

PRAGMA foreign_key_check;

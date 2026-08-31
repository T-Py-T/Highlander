PRAGMA foreign_keys = ON;

SELECT 'invoices_row_count' AS check_name, COUNT(*) AS value
FROM invoices;

SELECT 'payments_row_count' AS check_name, COUNT(*) AS value
FROM payments;

SELECT 'payment_orphans_row_count' AS check_name, COUNT(*) AS value
FROM payment_orphans;

SELECT 'invoice_status_column' AS check_name,
       COUNT(*) AS value
FROM pragma_table_info('invoices')
WHERE name = 'status'
  AND type = 'TEXT'
  AND "notnull" = 1
  AND dflt_value = '''open''';

SELECT 'null_or_empty_invoice_status_rows' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status IS NULL OR status = '';

SELECT 'non_open_legacy_invoice_status_rows' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status <> 'open';

SELECT 'orphan_p4_preserved' AS check_name, COUNT(*) AS value
FROM payment_orphans
WHERE id = 'p4'
  AND invoice_id = 'missing-invoice'
  AND amount_cents = 700
  AND created_at = '2024-01-07T10:00:00Z';

SELECT 'invoice_created_at_preserved' AS check_name, COUNT(*) AS value
FROM invoices
WHERE (id = 'inv1' AND created_at = '2024-01-03T10:00:00Z')
   OR (id = 'inv2' AND created_at = '2024-01-04T10:00:00Z')
   OR (id = 'inv3' AND created_at = '2024-01-05T10:00:00Z');

PRAGMA foreign_key_check;

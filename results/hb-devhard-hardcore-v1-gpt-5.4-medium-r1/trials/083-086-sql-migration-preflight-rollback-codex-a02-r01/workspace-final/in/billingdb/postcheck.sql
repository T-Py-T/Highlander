SELECT 'invoice_count' AS check_name, COUNT(*) AS value
FROM invoices;

SELECT 'payment_count' AS check_name, COUNT(*) AS value
FROM payments;

SELECT 'payment_orphan_count' AS check_name, COUNT(*) AS value
FROM payment_orphans;

SELECT
  'invoice_status_column' AS check_name,
  CASE
    WHEN EXISTS (
      SELECT 1
      FROM pragma_table_info('invoices')
      WHERE name = 'status'
        AND "notnull" = 1
        AND dflt_value = '''open'''
    ) THEN 'PASS'
    ELSE 'FAIL'
  END AS result;

SELECT
  'invoice_status_null_rows' AS check_name,
  COUNT(*) AS value
FROM invoices
WHERE status IS NULL;

SELECT
  'invoice_status_non_open_rows' AS check_name,
  COUNT(*) AS value
FROM invoices
WHERE status <> 'open';

SELECT
  'payments_invalid_invoice_refs' AS check_name,
  COUNT(*) AS value
FROM payments AS p
LEFT JOIN invoices AS i
  ON i.id = p.invoice_id
WHERE i.id IS NULL;

SELECT
  'orphan_p4_preserved' AS check_name,
  CASE
    WHEN EXISTS (
      SELECT 1
      FROM payment_orphans
      WHERE id = 'p4'
        AND invoice_id = 'missing-invoice'
        AND amount_cents = 700
        AND created_at = '2024-01-07T10:00:00Z'
    ) THEN 'PASS'
    ELSE 'FAIL'
  END AS result;

PRAGMA foreign_key_check;

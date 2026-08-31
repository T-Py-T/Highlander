SELECT 'invoices_count' AS check_name, COUNT(*) AS value FROM invoices;
SELECT 'payments_count' AS check_name, COUNT(*) AS value FROM payments;
SELECT 'payment_orphans_count' AS check_name, COUNT(*) AS value FROM payment_orphans;

SELECT 'invoice_status_null_rows' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status IS NULL;

SELECT 'invoice_status_open_rows' AS check_name, COUNT(*) AS value
FROM invoices
WHERE status = 'open';

SELECT 'invoice_created_at_preserved' AS check_name, COUNT(*) AS value
FROM invoices
WHERE (id, created_at) IN (
  ('inv1', '2024-01-03T10:00:00Z'),
  ('inv2', '2024-01-04T10:00:00Z'),
  ('inv3', '2024-01-05T10:00:00Z')
);

SELECT 'orphan_p4_preserved' AS check_name, COUNT(*) AS value
FROM payment_orphans
WHERE id = 'p4'
  AND invoice_id = 'missing-invoice'
  AND amount_cents = 700
  AND created_at = '2024-01-07T10:00:00Z'
  AND reason = 'missing_invoice';

SELECT 'payments_with_missing_invoice_refs' AS check_name, COUNT(*) AS value
FROM payments AS p
LEFT JOIN invoices AS i
  ON i.id = p.invoice_id
WHERE i.id IS NULL;

PRAGMA foreign_key_check;

-- Post-migration checks. Every SELECT should return the documented result.
PRAGMA foreign_keys;

-- Expected for the supplied schema: invoices=3, payments=3, orphans=1.
SELECT 'invoice_count' AS check_name, COUNT(*) AS value FROM invoices;
SELECT 'payment_count' AS check_name, COUNT(*) AS value FROM payments;
SELECT 'orphan_count' AS check_name, COUNT(*) AS value FROM payment_orphans;
SELECT 'orphan_p4_present' AS check_name, COUNT(*) AS value
FROM payment_orphans
WHERE id = 'p4'
  AND invoice_id = 'missing-invoice'
  AND amount_cents = 700
  AND created_at = '2024-01-07T10:00:00Z';

-- Status is present, non-null, and defaults to open for migrated rows.
SELECT 'status_not_null' AS check_name, COUNT(*) AS value
FROM invoices WHERE status IS NULL;
SELECT 'status_open' AS check_name, COUNT(*) AS value
FROM invoices WHERE status = 'open';
SELECT name, type, "notnull", dflt_value
FROM pragma_table_info('invoices')
WHERE name = 'status';

-- No retained payment can point at a missing invoice.
SELECT 'invalid_payment_references' AS check_name, COUNT(*) AS value
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;
PRAGMA foreign_key_check;

-- Historical timestamps must remain unchanged.
SELECT id, created_at FROM invoices ORDER BY id;

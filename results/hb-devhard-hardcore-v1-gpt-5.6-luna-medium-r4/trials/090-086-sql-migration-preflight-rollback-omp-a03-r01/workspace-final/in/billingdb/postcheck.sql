-- Post-migration assertions. Every SELECT should return the documented value.
SELECT 'invoice_count' AS check_name, COUNT(*) AS value FROM invoices;
SELECT 'payment_count' AS check_name, COUNT(*) AS value FROM payments;
SELECT 'orphan_count' AS check_name, COUNT(*) AS value FROM payment_orphans;
SELECT 'preserved_p4' AS check_name, COUNT(*) AS value
FROM payment_orphans
WHERE id = 'p4' AND invoice_id = 'missing-invoice'
  AND amount_cents = 700 AND created_at = '2024-01-07T10:00:00Z';
SELECT 'non_open_status_count' AS check_name, COUNT(*) AS value
FROM invoices WHERE status <> 'open' OR status IS NULL;
SELECT 'missing_status_default' AS check_name, COUNT(*) AS value
FROM invoices WHERE status = 'open';
SELECT 'invalid_payment_fk_count' AS check_name, COUNT(*) AS value
FROM payments AS p LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;
PRAGMA foreign_key_check;
PRAGMA foreign_keys;

-- Expected on the supplied seed: invoice_count=3, payment_count=3,
-- orphan_count=1, preserved_p4=1, non_open_status_count=0,
-- missing_status_default=3, invalid_payment_fk_count=0, foreign_keys=1.

-- Executable post-migration checks. Every result should be zero except the
-- row-count queries and the orphan-preservation query, which are informational.

PRAGMA foreign_keys = ON;

SELECT 'invoices_row_count' AS check_name, COUNT(*) AS value FROM invoices;
SELECT 'payments_row_count' AS check_name, COUNT(*) AS value FROM payments;
SELECT 'payment_orphans_row_count' AS check_name, COUNT(*) AS value FROM payment_orphans;

SELECT 'orphan_p4_preserved' AS check_name,
       CASE WHEN EXISTS (
         SELECT 1 FROM payment_orphans
         WHERE id = 'p4'
           AND invoice_id = 'missing-invoice'
           AND amount_cents = 700
           AND created_at = '2024-01-07T10:00:00Z'
       ) THEN 1 ELSE 0 END AS value;

SELECT 'invoice_status_nulls' AS check_name,
       COUNT(*) AS value FROM invoices WHERE status IS NULL;
SELECT 'invoice_status_not_open' AS check_name,
       COUNT(*) AS value FROM invoices WHERE status <> 'open';
SELECT 'invoice_created_at_changed' AS check_name,
       COUNT(*) AS value
FROM invoices
WHERE (id = 'inv1' AND created_at <> '2024-01-03T10:00:00Z')
   OR (id = 'inv2' AND created_at <> '2024-01-04T10:00:00Z')
   OR (id = 'inv3' AND created_at <> '2024-01-05T10:00:00Z');

SELECT 'foreign_key_violations' AS check_name,
       COUNT(*) AS value FROM pragma_foreign_key_check;
SELECT 'foreign_keys_enabled' AS check_name, foreign_keys AS value
FROM pragma_foreign_keys;

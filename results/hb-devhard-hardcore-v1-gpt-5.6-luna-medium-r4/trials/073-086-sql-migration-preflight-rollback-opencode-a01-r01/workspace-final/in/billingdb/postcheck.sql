-- Post-migration checks. A non-zero count in any failure column requires
-- stopping the release and investigating before accepting the migration.
PRAGMA foreign_keys = ON;

SELECT (SELECT COUNT(*) FROM invoices) AS invoice_count,
       CASE WHEN (SELECT COUNT(*) FROM invoices) = 3 THEN 0 ELSE 1 END AS invoice_count_failure;
SELECT (SELECT COUNT(*) FROM payments) AS valid_payment_count,
       CASE WHEN (SELECT COUNT(*) FROM payments) = 3 THEN 0 ELSE 1 END AS payment_count_failure;
SELECT (SELECT COUNT(*) FROM payment_orphans WHERE id = 'p4') AS p4_orphan_count,
       CASE WHEN (SELECT COUNT(*) FROM payment_orphans WHERE id = 'p4') = 1 THEN 0 ELSE 1 END AS p4_failure;
SELECT (SELECT COUNT(*) FROM invoices WHERE status = 'open') AS open_status_count,
       CASE WHEN (SELECT COUNT(*) FROM invoices WHERE status = 'open') = 3 THEN 0 ELSE 1 END AS status_failure;
SELECT (SELECT COUNT(*) FROM invoices WHERE id = 'inv1' AND created_at = '2024-01-03T10:00:00Z') AS historical_timestamp_match,
       CASE WHEN EXISTS (SELECT 1 FROM invoices WHERE id = 'inv1' AND created_at = '2024-01-03T10:00:00Z') THEN 0 ELSE 1 END AS timestamp_failure;
SELECT (SELECT COUNT(*) FROM payments AS p LEFT JOIN invoices AS i ON i.id = p.invoice_id WHERE i.id IS NULL) AS invalid_reference_count,
       CASE WHEN NOT EXISTS (SELECT 1 FROM payments AS p LEFT JOIN invoices AS i ON i.id = p.invoice_id WHERE i.id IS NULL) THEN 0 ELSE 1 END AS reference_failure;
SELECT (SELECT COUNT(*) FROM pragma_foreign_key_list('payments') WHERE "table" = 'invoices') AS payment_fk_count,
       CASE WHEN (SELECT COUNT(*) FROM pragma_foreign_key_list('payments') WHERE "table" = 'invoices') = 1 THEN 0 ELSE 1 END AS foreign_key_failure;
PRAGMA foreign_key_check;

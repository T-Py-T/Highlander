-- Post-migration checks. Each result row is a check name and observed value.
SELECT 'invoice_count' AS check_name, COUNT(*) AS observed, 3 AS expected FROM invoices;
SELECT 'payment_count' AS check_name, COUNT(*) AS observed, 3 AS expected FROM payments;
SELECT 'orphan_count' AS check_name, COUNT(*) AS observed, 1 AS expected FROM payment_orphans;
SELECT 'orphan_p4_preserved' AS check_name, COUNT(*) AS observed, 1 AS expected
FROM payment_orphans
WHERE id = 'p4' AND invoice_id = 'missing-invoice' AND amount_cents = 700
  AND created_at = '2024-01-07T10:00:00Z';
SELECT 'non_open_statuses' AS check_name, COUNT(*) AS observed, 0 AS expected
FROM invoices WHERE status <> 'open' OR status IS NULL;
SELECT 'invalid_payment_references' AS check_name, COUNT(*) AS observed, 0 AS expected
FROM payments AS p LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;
SELECT 'foreign_key_violations' AS check_name, COUNT(*) AS observed, 0 AS expected
FROM pragma_foreign_key_check;
SELECT 'payments_fk_definition' AS check_name, COUNT(*) AS observed, 1 AS expected
FROM pragma_foreign_key_list('payments')
WHERE "table" = 'invoices' AND "from" = 'invoice_id' AND "to" = 'id';

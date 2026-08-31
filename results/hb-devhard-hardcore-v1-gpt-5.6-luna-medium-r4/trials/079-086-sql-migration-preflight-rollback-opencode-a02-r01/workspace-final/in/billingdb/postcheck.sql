-- Post-migration checks. A zero-valued check column means the invariant holds.
SELECT 'invoice_count' AS check_name, COUNT(*) AS observed, 3 AS expected
FROM invoices;
SELECT 'payment_count_after_orphan_move' AS check_name, COUNT(*) AS observed, 3 AS expected
FROM payments;
SELECT 'orphan_count' AS check_name, COUNT(*) AS observed, 1 AS expected
FROM payment_orphans;
SELECT 'orphan_p4_preserved' AS check_name, COUNT(*) AS observed, 1 AS expected
FROM payment_orphans
WHERE id = 'p4' AND invoice_id = 'missing-invoice' AND amount_cents = 700
  AND created_at = '2024-01-07T10:00:00Z';
SELECT 'all_invoice_status_open' AS check_name, COUNT(*) AS violations
FROM invoices WHERE status IS NULL OR status <> 'open';
SELECT 'invoice_created_at_preserved' AS check_name, COUNT(*) AS violations
FROM invoices
WHERE (id, created_at) NOT IN (
  VALUES ('inv1', '2024-01-03T10:00:00Z'),
         ('inv2', '2024-01-04T10:00:00Z'),
         ('inv3', '2024-01-05T10:00:00Z')
);
SELECT 'foreign_key_violations' AS check_name, COUNT(*) AS violations
FROM pragma_foreign_key_check;
SELECT 'payments_without_orphan_references' AS check_name, COUNT(*) AS violations
FROM payments AS p LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;
SELECT name, sql FROM sqlite_master
WHERE type = 'table' AND name IN ('invoices', 'payments', 'payment_orphans')
ORDER BY name;

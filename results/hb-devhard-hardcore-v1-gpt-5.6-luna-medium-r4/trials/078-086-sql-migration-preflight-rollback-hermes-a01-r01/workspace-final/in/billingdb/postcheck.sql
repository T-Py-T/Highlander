-- Post-migration checks.  A successful check returns no rows from the
-- failure queries, followed by diagnostic counts and schema/FK evidence.
PRAGMA foreign_keys = ON;

SELECT 'invoice_count_mismatch' AS check_name
WHERE (SELECT COUNT(*) FROM invoices) <> 3;

SELECT 'payment_count_mismatch' AS check_name
WHERE (SELECT COUNT(*) FROM payments) <> 3;

SELECT 'orphan_missing_or_changed' AS check_name
WHERE NOT EXISTS (
  SELECT 1 FROM payment_orphans
  WHERE id = 'p4' AND invoice_id = 'missing-invoice'
    AND amount_cents = 700 AND created_at = '2024-01-07T10:00:00Z'
);

SELECT 'invalid_live_payment_reference' AS check_name
WHERE EXISTS (
  SELECT 1 FROM payments AS p
  LEFT JOIN invoices AS i ON i.id = p.invoice_id
  WHERE i.id IS NULL
);

SELECT 'invoice_status_definition_missing' AS check_name
WHERE NOT EXISTS (
  SELECT 1 FROM pragma_table_info('invoices')
  WHERE name = 'status' AND "notnull" = 1 AND dflt_value = '''open'''
);

SELECT 'invoice_created_at_changed' AS check_name
WHERE EXISTS (
  SELECT 1 FROM invoices
  WHERE (id, created_at) NOT IN (
    VALUES ('inv1','2024-01-03T10:00:00Z'),
           ('inv2','2024-01-04T10:00:00Z'),
           ('inv3','2024-01-05T10:00:00Z')
  )
);

SELECT 'foreign_key_definition_missing' AS check_name
WHERE NOT EXISTS (
  SELECT 1 FROM pragma_foreign_key_list('payments')
  WHERE "table" = 'invoices' AND "from" = 'invoice_id' AND "to" = 'id'
);

SELECT 'foreign_key_violations' AS check_name, * FROM pragma_foreign_key_check;

SELECT 'invoices' AS table_name, COUNT(*) AS row_count FROM invoices
UNION ALL SELECT 'payments', COUNT(*) FROM payments
UNION ALL SELECT 'payment_orphans', COUNT(*) FROM payment_orphans;

SELECT id, status FROM invoices ORDER BY id;
SELECT foreign_keys AS foreign_keys_enabled FROM pragma_foreign_keys;

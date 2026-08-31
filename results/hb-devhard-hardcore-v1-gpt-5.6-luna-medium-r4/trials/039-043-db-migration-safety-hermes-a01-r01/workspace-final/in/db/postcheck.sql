-- Verification queries for the migrated database. Expected scalar results are
-- documented in comments; each query returns evidence rather than mutating data.
PRAGMA foreign_keys = ON;

-- Expected: 6 users and 4 orders.
SELECT 'user_count' AS check_name, COUNT(*) AS actual, 6 AS expected FROM users;
SELECT 'order_count' AS check_name, COUNT(*) AS actual, 4 AS expected FROM orders;

-- Expected: zero missing migrated users and zero changed order references.
SELECT 'order_reference_integrity' AS check_name, COUNT(*) AS violations
FROM orders o LEFT JOIN users u ON u.id = o.user_id
WHERE u.id IS NULL;
SELECT 'expected_order_references' AS check_name, COUNT(*) AS violations
FROM orders o
LEFT JOIN (SELECT 'o1' AS id, 'u1' AS user_id UNION ALL
           SELECT 'o2', 'u4' UNION ALL
           SELECT 'o3', 'u5' UNION ALL
           SELECT 'o4', 'u6') AS expected
  ON expected.id = o.id AND expected.user_id = o.user_id
WHERE expected.id IS NULL;
SELECT 'expected_dirty_user_orders' AS check_name, COUNT(*) AS actual, 3 AS expected
FROM orders WHERE user_id IN ('u4', 'u5', 'u6');

-- Expected: exactly the deterministic cleanup values.
SELECT id, email, CASE id
    WHEN 'u4' THEN 'ada+u4@example.com'
    WHEN 'u5' THEN 'missing+u5@example.invalid'
    WHEN 'u6' THEN 'missing+u6@example.invalid'
END AS expected_email
FROM users WHERE id IN ('u4', 'u5', 'u6') ORDER BY id;

-- Expected: zero NULL/blank emails and zero duplicate email groups.
SELECT 'null_or_blank_emails' AS check_name, COUNT(*) AS violations
FROM users WHERE email IS NULL OR trim(email) = '';
SELECT 'duplicate_emails' AS check_name, COUNT(*) AS duplicate_groups
FROM (SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1);

-- Expected: status is non-null and all current rows are active.
SELECT 'invalid_status_rows' AS check_name, COUNT(*) AS violations
FROM users WHERE status IS NULL OR status <> 'active';

-- Schema checks: expected users columns include status with NOT NULL and a
-- unique email index/constraint; orders must still reference users(id).
PRAGMA table_info(users);
PRAGMA index_list(users);
PRAGMA foreign_key_list(orders);

SELECT 'email_not_null_declared' AS check_name,
       (SELECT "notnull" FROM pragma_table_info('users') WHERE name = 'email') AS actual,
       1 AS expected;
SELECT 'status_not_null_declared' AS check_name,
       (SELECT "notnull" FROM pragma_table_info('users') WHERE name = 'status') AS actual,
       1 AS expected;
SELECT 'status_default' AS check_name,
       (SELECT dflt_value FROM pragma_table_info('users') WHERE name = 'status') AS actual,
       '''active''' AS expected;
SELECT 'unique_email_index' AS check_name, COUNT(*) AS actual, 1 AS expected
FROM pragma_index_list('users') AS il
WHERE il."unique" = 1
  AND EXISTS (SELECT 1 FROM pragma_index_info(il.name) AS ii WHERE ii.name = 'email');
SELECT 'orders_user_fk' AS check_name, COUNT(*) AS actual, 1 AS expected
FROM pragma_foreign_key_list('orders')
WHERE "table" = 'users' AND "from" = 'user_id' AND "to" = 'id';

-- Expected counts for the supplied legacy fixture: 6 users and 4 orders.
SELECT 'user_count' AS check_name, COUNT(*) AS value FROM users;
SELECT 'order_count' AS check_name, COUNT(*) AS value FROM orders;

-- Every order still points at an existing user, including dirty-user orders.
SELECT 'orphan_orders' AS check_name, COUNT(*) AS value
FROM orders AS o
LEFT JOIN users AS u ON u.id = o.user_id
WHERE u.id IS NULL;
SELECT 'dirty_user_orders' AS check_name, GROUP_CONCAT(o.id, ',') AS value
FROM orders AS o
WHERE o.user_id IN ('u4', 'u5', 'u6');

-- Deterministic cleanup results.
SELECT 'u4_email' AS check_name, email AS value FROM users WHERE id = 'u4';
SELECT 'u5_email' AS check_name, email AS value FROM users WHERE id = 'u5';
SELECT 'u6_email' AS check_name, email AS value FROM users WHERE id = 'u6';

-- Constraint checks: these counts must all be zero.
SELECT 'null_emails' AS check_name, COUNT(*) AS value
FROM users WHERE email IS NULL;
SELECT 'blank_emails' AS check_name, COUNT(*) AS value
FROM users WHERE trim(email) = '';
SELECT 'duplicate_emails' AS check_name, COUNT(*) AS value
FROM (SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1);
SELECT 'invalid_status' AS check_name, COUNT(*) AS value
FROM users WHERE status IS NULL OR status <> 'active';

-- Schema-level confirmation of NOT NULL/UNIQUE email and NOT NULL status.
SELECT 'users_columns' AS check_name, name, type, "notnull", dflt_value
FROM pragma_table_info('users')
WHERE name IN ('email', 'status');
SELECT 'users_unique_indexes' AS check_name, name, [unique]
FROM pragma_index_list('users');

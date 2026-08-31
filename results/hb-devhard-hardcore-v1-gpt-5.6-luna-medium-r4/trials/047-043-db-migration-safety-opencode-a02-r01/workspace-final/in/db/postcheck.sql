-- Expected counts for the supplied seed data.
SELECT 'users_row_count' AS check_name, COUNT(*) AS actual, 6 AS expected
FROM users;
SELECT 'orders_row_count' AS check_name, COUNT(*) AS actual, 4 AS expected
FROM orders;

-- Every order remains attached to the same existing user id.
SELECT 'dependent_order_count' AS check_name, COUNT(*) AS actual, 3 AS expected
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6');
SELECT id, user_id
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- Deterministic cleanup results.
SELECT id, email
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- Constraint and default inspection.
SELECT name, "notnull", dflt_value
FROM pragma_table_info('users')
WHERE name IN ('email', 'status')
ORDER BY name;
SELECT name, [unique]
FROM pragma_index_list('users')
WHERE [unique] = 1;

-- These must both return zero.
SELECT 'null_or_blank_emails' AS check_name, COUNT(*) AS violations
FROM users
WHERE email IS NULL OR TRIM(email) = '';
SELECT 'duplicate_emails' AS check_name, COUNT(*) AS violations
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

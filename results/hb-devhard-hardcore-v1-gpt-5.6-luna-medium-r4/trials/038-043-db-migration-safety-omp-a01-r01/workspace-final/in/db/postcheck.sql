-- Execute after migration. Each SELECT should return the expected value below it.
PRAGMA foreign_keys = ON;

-- Expected: 6 users and 4 orders.
SELECT 'user_count' AS check_name, COUNT(*) AS actual, 6 AS expected FROM users;
SELECT 'order_count' AS check_name, COUNT(*) AS actual, 4 AS expected FROM orders;

-- Expected: 0 means every order retained its original user reference.
SELECT 'order_reference_mismatches' AS check_name, COUNT(*) AS actual, 0 AS expected
FROM (
    SELECT 'o1' AS order_id, 'u1' AS user_id UNION ALL
    SELECT 'o2', 'u4' UNION ALL
    SELECT 'o3', 'u5' UNION ALL
    SELECT 'o4', 'u6'
) AS expected_orders
LEFT JOIN orders AS actual_orders
    ON actual_orders.id = expected_orders.order_id
   AND actual_orders.user_id = expected_orders.user_id
WHERE actual_orders.id IS NULL;

-- Expected: each query returns exactly one row with the specified email.
SELECT id, email FROM users WHERE id IN ('u4', 'u5', 'u6') ORDER BY id;

-- Expected: all rows have non-null/non-blank unique emails and active status.
SELECT 'invalid_email_rows' AS check_name, COUNT(*) AS actual, 0 AS expected
FROM users WHERE email IS NULL OR trim(email) = '';
SELECT 'duplicate_email_groups' AS check_name, COUNT(*) AS actual, 0 AS expected
FROM (SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1);
SELECT 'invalid_status_rows' AS check_name, COUNT(*) AS actual, 0 AS expected
FROM users WHERE status IS NULL;

-- Expected: 1 for each constraint/index.
SELECT 'users_email_unique_index' AS check_name, COUNT(*) AS actual, 1 AS expected
FROM pragma_index_list('users') WHERE name = 'sqlite_autoindex_users_1' AND [unique] = 1;
SELECT 'users_email_not_null' AS check_name, COUNT(*) AS actual, 1 AS expected
FROM pragma_table_info('users') WHERE name = 'email' AND "notnull" = 1;
SELECT 'users_status_not_null' AS check_name, COUNT(*) AS actual, 1 AS expected
FROM pragma_table_info('users') WHERE name = 'status' AND "notnull" = 1;

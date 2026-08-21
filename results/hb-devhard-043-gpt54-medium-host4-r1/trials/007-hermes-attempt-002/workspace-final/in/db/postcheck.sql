SELECT 'users_row_count' AS check_name, COUNT(*) AS actual_count, 6 AS expected_count
FROM users;

SELECT 'orders_row_count' AS check_name, COUNT(*) AS actual_count, 4 AS expected_count
FROM orders;

SELECT 'orphaned_orders' AS check_name, COUNT(*) AS actual_count, 0 AS expected_count
FROM orders o
LEFT JOIN users u ON u.id = o.user_id
WHERE u.id IS NULL;

SELECT 'dirty_user_cleanup' AS check_name, id, email
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT 'remaining_null_or_blank_emails' AS check_name, COUNT(*) AS actual_count, 0 AS expected_count
FROM users
WHERE email IS NULL OR trim(email) = '';

SELECT 'remaining_duplicate_emails' AS check_name, COUNT(*) AS actual_count, 0 AS expected_count
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT 'null_status_rows' AS check_name, COUNT(*) AS actual_count, 0 AS expected_count
FROM users
WHERE status IS NULL;

SELECT 'dependent_orders_for_dirty_users' AS check_name, o.id AS order_id, o.user_id, o.total_cents
FROM orders o
WHERE o.user_id IN ('u4', 'u5', 'u6')
ORDER BY o.id;

PRAGMA table_info('users');

SELECT 'users_table_sql' AS check_name, sql
FROM sqlite_master
WHERE type = 'table' AND name = 'users';

PRAGMA foreign_key_check;

SELECT 'user_row_count' AS check_name, COUNT(*) AS actual_count, 6 AS expected_count
FROM users;

SELECT 'order_row_count' AS check_name, COUNT(*) AS actual_count, 4 AS expected_count
FROM orders;

SELECT 'dirty_user_orders_preserved' AS check_name, user_id, GROUP_CONCAT(id, ',') AS order_ids, COUNT(*) AS order_count
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
GROUP BY user_id
ORDER BY user_id;

SELECT 'dirty_user_email_cleanup' AS check_name, id, email
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT 'null_or_blank_email_count' AS check_name, COUNT(*) AS invalid_email_count, 0 AS expected_count
FROM users
WHERE email IS NULL OR trim(email) = '';

SELECT 'duplicate_email_group_count' AS check_name, COUNT(*) AS duplicate_group_count, 0 AS expected_count
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT 'status_null_or_non_active_count' AS check_name, COUNT(*) AS invalid_status_count, 0 AS expected_count
FROM users
WHERE status IS NULL OR trim(status) = '' OR status <> 'active';

SELECT 'users_status_column' AS check_name, name, type, "notnull", dflt_value
FROM pragma_table_info('users')
WHERE name = 'status';

SELECT 'users_table_definition' AS check_name, sql
FROM sqlite_schema
WHERE type = 'table' AND name = 'users';

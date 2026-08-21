-- Post-migration verification queries.

.headers on
.mode column

SELECT 'user_row_count' AS check_name, COUNT(*) AS actual, 6 AS expected
FROM users;

SELECT 'order_row_count' AS check_name, COUNT(*) AS actual, 4 AS expected
FROM orders;

SELECT 'orders_for_dirty_users' AS check_name, user_id, COUNT(*) AS order_count
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
GROUP BY user_id
ORDER BY user_id;

SELECT 'dirty_user_emails' AS check_name, id, email
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT 'duplicate_email_count' AS check_name, COUNT(*) AS duplicates
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT 'null_or_blank_email_count' AS check_name, COUNT(*) AS invalid_emails
FROM users
WHERE email IS NULL OR trim(email) = '';

SELECT 'non_active_status_count' AS check_name, COUNT(*) AS non_active_statuses
FROM users
WHERE status IS NULL OR status <> 'active';

SELECT 'users_schema_columns' AS check_name, name, type, "notnull", dflt_value, pk
FROM pragma_table_info('users')
ORDER BY cid;

PRAGMA foreign_key_check;

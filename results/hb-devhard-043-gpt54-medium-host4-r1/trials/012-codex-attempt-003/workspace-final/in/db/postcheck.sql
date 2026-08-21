SELECT 'user_row_count' AS check_name, COUNT(*) AS actual, 6 AS expected
FROM users;

SELECT 'order_row_count' AS check_name, COUNT(*) AS actual, 4 AS expected
FROM orders;

SELECT 'dirty_user_order_preservation' AS check_name, user_id, COUNT(*) AS order_count
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
GROUP BY user_id
ORDER BY user_id;

SELECT 'cleaned_dirty_emails' AS check_name, id, email
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT 'null_or_blank_emails' AS check_name, COUNT(*) AS actual, 0 AS expected
FROM users
WHERE email IS NULL OR TRIM(email) = '';

SELECT 'duplicate_email_groups' AS check_name, COUNT(*) AS actual, 0 AS expected
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT 'status_values' AS check_name, status, COUNT(*) AS row_count
FROM users
GROUP BY status
ORDER BY status;

SELECT 'users_table_sql' AS check_name, sql
FROM sqlite_master
WHERE type = 'table' AND name = 'users';

PRAGMA table_info('users');
PRAGMA index_list('users');

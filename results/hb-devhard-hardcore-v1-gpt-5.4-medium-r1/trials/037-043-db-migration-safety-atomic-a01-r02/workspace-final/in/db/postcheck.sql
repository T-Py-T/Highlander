-- Expected preserved counts from schema.sql
SELECT 'users_row_count' AS check_name, COUNT(*) AS actual, 6 AS expected
FROM users;

SELECT 'orders_row_count' AS check_name, COUNT(*) AS actual, 4 AS expected
FROM orders;

-- Dirty-user orders must still point to the same user ids.
SELECT 'dirty_user_order_counts' AS check_name, user_id, COUNT(*) AS order_count
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
GROUP BY user_id
ORDER BY user_id;

-- Cleaned emails must match the required deterministic values.
SELECT 'dirty_user_email_cleanup' AS check_name, id, email
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- Data-level checks for the new constraints.
SELECT 'null_email_count' AS check_name, COUNT(*) AS actual, 0 AS expected
FROM users
WHERE email IS NULL;

SELECT 'blank_email_count' AS check_name, COUNT(*) AS actual, 0 AS expected
FROM users
WHERE length(trim(email)) = 0;

SELECT 'duplicate_email_group_count' AS check_name, COUNT(*) AS actual, 0 AS expected
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT 'null_status_count' AS check_name, COUNT(*) AS actual, 0 AS expected
FROM users
WHERE status IS NULL;

SELECT 'status_value_counts' AS check_name, status, COUNT(*) AS user_count
FROM users
GROUP BY status
ORDER BY status;

-- Schema inspection checks.
PRAGMA table_info(users);
PRAGMA index_list(users);
SELECT sql
FROM sqlite_master
WHERE type = 'table' AND name = 'users';

PRAGMA foreign_key_check;

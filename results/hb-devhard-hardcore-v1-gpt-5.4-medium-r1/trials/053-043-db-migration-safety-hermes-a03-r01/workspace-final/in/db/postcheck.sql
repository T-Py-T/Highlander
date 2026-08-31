-- Row-count preservation
SELECT 'users_row_count' AS check_name, COUNT(*) AS actual_count, 6 AS expected_count
FROM users;

SELECT 'orders_row_count' AS check_name, COUNT(*) AS actual_count, 4 AS expected_count
FROM orders;

-- Dependent order preservation for dirty users
SELECT 'dirty_user_order_links' AS check_name, user_id, COUNT(*) AS order_count, GROUP_CONCAT(id, ',') AS order_ids
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
GROUP BY user_id
ORDER BY user_id;

-- Deterministic cleaned email values
SELECT 'cleaned_dirty_user_emails' AS check_name, id, email
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- Data-level constraint checks
SELECT 'email_null_or_blank_count' AS check_name, COUNT(*) AS violating_rows
FROM users
WHERE email IS NULL OR trim(email) = '';

SELECT 'email_duplicate_group_count' AS check_name, COUNT(*) AS violating_groups
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT 'status_null_count' AS check_name, COUNT(*) AS violating_rows
FROM users
WHERE status IS NULL;

SELECT 'status_distribution' AS check_name, status, COUNT(*) AS row_count
FROM users
GROUP BY status
ORDER BY status;

-- Schema/constraint presence checks
SELECT 'users_table_sql' AS check_name, sql
FROM sqlite_master
WHERE type = 'table' AND name = 'users';

SELECT 'users_unique_index_count' AS check_name, COUNT(*) AS present
FROM pragma_index_list('users')
WHERE "unique" = 1;

PRAGMA foreign_key_check;

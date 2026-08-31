-- Expected preserved counts from schema.sql:
-- users: 6
-- orders: 4

SELECT 'user_count' AS check_name, COUNT(*) AS observed, 6 AS expected
FROM users;

SELECT 'order_count' AS check_name, COUNT(*) AS observed, 4 AS expected
FROM orders;

SELECT 'dirty_user_email_cleanup' AS check_name, id, email
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT 'dependent_order_preservation' AS check_name, id, user_id, total_cents
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT 'duplicate_email_rows' AS check_name, email, COUNT(*) AS duplicate_count
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

SELECT 'null_or_blank_email_rows' AS check_name, COUNT(*) AS bad_rows
FROM users
WHERE email IS NULL OR LENGTH(TRIM(email)) = 0;

SELECT 'null_or_blank_status_rows' AS check_name, COUNT(*) AS bad_rows
FROM users
WHERE status IS NULL OR LENGTH(TRIM(status)) = 0;

SELECT 'non_active_status_rows' AS check_name, COUNT(*) AS rows_found
FROM users
WHERE status <> 'active';

PRAGMA table_info(users);

SELECT sql
FROM sqlite_master
WHERE type = 'table' AND name = 'users';

PRAGMA index_list(users);

PRAGMA foreign_key_check;

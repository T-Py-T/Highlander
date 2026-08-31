PRAGMA foreign_keys = ON;

-- Expected source cardinalities: six users and four orders.
SELECT 'user_count' AS check_name, COUNT(*) AS actual, 6 AS expected FROM users;
SELECT 'order_count' AS check_name, COUNT(*) AS actual, 4 AS expected FROM orders;

-- No order was lost or pointed at a different user.
SELECT 'orders_by_user' AS check_name, user_id, COUNT(*) AS order_count
FROM orders
GROUP BY user_id
ORDER BY user_id;
WITH expected(order_id, user_id) AS (
    VALUES ('o2', 'u4'), ('o3', 'u5'), ('o4', 'u6')
)
SELECT 'dirty_order_reference_mismatch' AS check_name,
       expected.order_id, expected.user_id, orders.user_id AS actual_user_id
FROM expected LEFT JOIN orders ON orders.id = expected.order_id
WHERE orders.id IS NULL OR orders.user_id <> expected.user_id;
SELECT 'orphan_orders' AS check_name, COUNT(*) AS actual
FROM orders AS o LEFT JOIN users AS u ON u.id = o.user_id
WHERE u.id IS NULL;

-- Required deterministic cleanup results.
SELECT 'u4_email' AS check_name, email FROM users WHERE id = 'u4';
SELECT 'u5_email' AS check_name, email FROM users WHERE id = 'u5';
SELECT 'u6_email' AS check_name, email FROM users WHERE id = 'u6';

-- These must return zero. PRAGMA checks expose NOT NULL and UNIQUE metadata.
SELECT 'null_or_blank_emails' AS check_name, COUNT(*) AS actual
FROM users WHERE email IS NULL OR trim(email) = '';
SELECT 'duplicate_emails' AS check_name, COUNT(*) AS actual
FROM (SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1);
SELECT 'null_statuses' AS check_name, COUNT(*) AS actual
FROM users WHERE status IS NULL;
PRAGMA table_info(users);
PRAGMA index_list(users);

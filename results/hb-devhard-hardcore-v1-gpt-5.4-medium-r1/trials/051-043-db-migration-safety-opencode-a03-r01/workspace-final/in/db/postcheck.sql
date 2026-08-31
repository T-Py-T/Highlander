-- Row counts should remain unchanged.
SELECT 'users_row_count' AS check_name, COUNT(*) AS actual_count, 6 AS expected_count
FROM users;

SELECT 'orders_row_count' AS check_name, COUNT(*) AS actual_count, 4 AS expected_count
FROM orders;

-- Dependent orders for dirty users must still point at the same user ids.
SELECT o.id AS order_id, o.user_id, u.email, u.status
FROM orders AS o
JOIN users AS u ON u.id = o.user_id
WHERE o.user_id IN ('u4', 'u5', 'u6')
ORDER BY o.id;

-- Deterministic dirty-email cleanup results.
SELECT id, email, status, created_at
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- Constraint-oriented checks after migration.
SELECT 'null_or_blank_emails' AS check_name, COUNT(*) AS violation_count
FROM users
WHERE email IS NULL OR TRIM(email) = '';

SELECT 'duplicate_emails' AS check_name, COUNT(*) AS violation_count
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT 'non_active_or_null_status' AS check_name, COUNT(*) AS violation_count
FROM users
WHERE status IS NULL OR status <> 'active';

PRAGMA foreign_key_check;

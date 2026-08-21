-- Row counts should remain unchanged.
SELECT 'users_row_count' AS check_name, COUNT(*) AS actual_count
FROM users;

SELECT 'orders_row_count' AS check_name, COUNT(*) AS actual_count
FROM orders;

-- Dependent orders for dirty users must still point at the same user ids.
SELECT o.id, o.user_id, o.total_cents, o.created_at
FROM orders AS o
WHERE o.user_id IN ('u4', 'u5', 'u6')
ORDER BY o.id;

-- Cleaned legacy emails must match the deterministic migration policy.
SELECT id, email, status, created_at
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- There should be no null, blank, or duplicate emails after migration.
SELECT 'null_or_blank_email_rows' AS check_name, COUNT(*) AS violation_count
FROM users
WHERE email IS NULL OR TRIM(email) = '';

SELECT 'duplicate_email_groups' AS check_name, COUNT(*) AS violation_count
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

-- Status must be present on every row and currently canonicalized to active.
SELECT 'non_active_or_null_status_rows' AS check_name, COUNT(*) AS violation_count
FROM users
WHERE status IS NULL OR status <> 'active';

-- Schema-level enforcement checks for future writes.
SELECT sql
FROM sqlite_master
WHERE type = 'table' AND name = 'users';

PRAGMA index_list('users');
PRAGMA table_info('users');
PRAGMA foreign_key_check;

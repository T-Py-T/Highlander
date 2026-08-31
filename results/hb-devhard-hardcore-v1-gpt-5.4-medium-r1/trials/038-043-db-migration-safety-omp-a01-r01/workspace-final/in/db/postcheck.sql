-- Row counts should remain unchanged.
SELECT 'users_count' AS check_name, COUNT(*) AS actual, 6 AS expected
FROM users;

SELECT 'orders_count' AS check_name, COUNT(*) AS actual, 4 AS expected
FROM orders;

-- Dirty-user orders must still reference the same user ids.
SELECT o.id AS order_id, o.user_id, u.email, u.status
FROM orders AS o
JOIN users AS u ON u.id = o.user_id
WHERE o.user_id IN ('u4', 'u5', 'u6')
ORDER BY o.id;

-- Dirty emails must be cleaned to deterministic values.
SELECT id, email
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- Historical timestamps must remain unchanged for migrated rows.
SELECT id, created_at
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- All users must have non-null, non-blank, unique emails and active status after migration.
SELECT
    SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END) AS null_emails,
    SUM(CASE WHEN trim(email) = '' THEN 1 ELSE 0 END) AS blank_emails,
    COUNT(*) - COUNT(DISTINCT email) AS duplicate_emails,
    SUM(CASE WHEN status IS NULL THEN 1 ELSE 0 END) AS null_statuses,
    SUM(CASE WHEN status <> 'active' THEN 1 ELSE 0 END) AS non_active_statuses
FROM users;

-- Schema-level checks for post-migration constraints.
SELECT sql
FROM sqlite_master
WHERE type = 'table'
  AND name = 'users';

PRAGMA index_list('users');

PRAGMA foreign_key_check;

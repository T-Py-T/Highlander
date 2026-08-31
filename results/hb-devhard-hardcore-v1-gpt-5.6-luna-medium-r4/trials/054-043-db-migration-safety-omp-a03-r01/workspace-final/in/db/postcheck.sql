-- Expected source counts: users=6, orders=4.
SELECT 'users_count' AS check_name, COUNT(*) AS actual, 6 AS expected FROM users;
SELECT 'orders_count' AS check_name, COUNT(*) AS actual, 4 AS expected FROM orders;

-- Every dependent order remains attached to its original user.
SELECT 'dirty_order_references' AS check_name,
       COUNT(*) AS actual,
       3 AS expected
FROM orders
WHERE (id, user_id) IN (('o2', 'u4'), ('o3', 'u5'), ('o4', 'u6'));

-- Deterministic cleanup values.
SELECT id, email FROM users WHERE id IN ('u4', 'u5', 'u6') ORDER BY id;

-- Constraint checks: no null/blank emails and no duplicate normalized values.
-- Each dirty user has its required deterministic value.
SELECT 'cleaned_dirty_emails' AS check_name,
       SUM(CASE
           WHEN id = 'u4' AND email = 'ada+u4@example.com' THEN 0
           WHEN id = 'u5' AND email = 'missing+u5@example.invalid' THEN 0
           WHEN id = 'u6' AND email = 'missing+u6@example.invalid' THEN 0
           ELSE 1
       END) AS violations
FROM users
WHERE id IN ('u4', 'u5', 'u6');
SELECT 'null_or_blank_emails' AS check_name, COUNT(*) AS violations
FROM users WHERE email IS NULL OR trim(email) = '';
SELECT 'duplicate_emails' AS check_name,
       COUNT(*) - COUNT(DISTINCT email) AS violations
FROM users;
SELECT 'invalid_status_rows' AS check_name, COUNT(*) AS violations
FROM users WHERE status IS NULL;

-- Schema-level checks for NOT NULL and UNIQUE declarations.
SELECT name, sql FROM sqlite_master
WHERE type = 'table' AND name = 'users';
PRAGMA index_list('users');
PRAGMA table_info('users');

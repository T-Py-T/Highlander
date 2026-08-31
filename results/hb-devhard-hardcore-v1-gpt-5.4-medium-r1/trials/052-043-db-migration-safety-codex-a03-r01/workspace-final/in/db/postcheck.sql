-- Expected: `user_count` = 6
SELECT COUNT(*) AS user_count FROM users;

-- Expected: `order_count` = 4
SELECT COUNT(*) AS order_count FROM orders;

-- Expected: no rows returned
SELECT user_id, COUNT(*) AS order_count
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
GROUP BY user_id
HAVING COUNT(*) <> 1;

-- Expected:
-- u4|ada+u4@example.com
-- u5|missing+u5@example.invalid
-- u6|missing+u6@example.invalid
SELECT id, email
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- Expected: 0
SELECT COUNT(*) AS null_or_blank_emails
FROM users
WHERE email IS NULL OR TRIM(email) = '';

-- Expected: no rows returned
SELECT email, COUNT(*) AS duplicate_count
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

-- Expected: 6
SELECT COUNT(*) AS active_status_rows
FROM users
WHERE status = 'active';

-- Inspect for schema enforcement:
PRAGMA table_info(users);

-- Inspect for the table-level `UNIQUE` and `NOT NULL` constraints:
SELECT sql
FROM sqlite_schema
WHERE type = 'table' AND name = 'users';

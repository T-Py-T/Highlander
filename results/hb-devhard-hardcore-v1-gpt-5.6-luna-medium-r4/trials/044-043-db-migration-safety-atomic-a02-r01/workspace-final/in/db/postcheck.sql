-- Run after migration. Every query should return the stated result.

-- Row counts: 6 users and 4 orders for the supplied preflight data.
SELECT 'users_count' AS check_name, COUNT(*) AS actual, 6 AS expected
FROM users;
SELECT 'orders_count' AS check_name, COUNT(*) AS actual, 4 AS expected
FROM orders;

-- Every order still points to an existing user; dirty-user dependents remain.
SELECT 'orphan_orders' AS check_name, COUNT(*) AS actual
FROM orders o LEFT JOIN users u ON u.id = o.user_id
WHERE u.id IS NULL;
SELECT 'dirty_user_orders' AS check_name, GROUP_CONCAT(id, ',') AS order_ids
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6');

-- Deterministic cleanup values; mismatch count must be zero.
SELECT 'dirty_email_mismatches' AS check_name, COUNT(*) AS actual
FROM users
WHERE (id = 'u4' AND email <> 'ada+u4@example.com')
   OR (id = 'u5' AND email <> 'missing+u5@example.invalid')
   OR (id = 'u6' AND email <> 'missing+u6@example.invalid');
SELECT id, email FROM users WHERE id IN ('u4', 'u5', 'u6') ORDER BY id;

-- Constraint checks: both counts must be zero.
SELECT 'null_emails' AS check_name, COUNT(*) AS actual
FROM users WHERE email IS NULL;
SELECT 'blank_emails' AS check_name, COUNT(*) AS actual
FROM users WHERE trim(email) = '';
SELECT 'duplicate_emails' AS check_name, COUNT(*) AS actual
FROM (SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1);

-- Schema checks: users.email is NOT NULL and UNIQUE; status is NOT NULL with
-- an active default (table_info columns: name, type, notnull, dflt_value).
SELECT name, type, "notnull", dflt_value
FROM pragma_table_info('users')
WHERE name IN ('email', 'status')
ORDER BY name;
SELECT 'email_unique_index_count' AS check_name, COUNT(*) AS actual
FROM pragma_index_list('users')
WHERE [unique] = 1;

-- Foreign-key integrity.
PRAGMA foreign_key_check;

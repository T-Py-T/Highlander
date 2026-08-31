-- Post-migration verification queries. Each query returns the observed value;
-- compare count/check results with the expected values in the comments.

-- Expected: users=6, orders=4.
SELECT 'users_count' AS check_name, COUNT(*) AS observed, 6 AS expected FROM users;
SELECT 'orders_count' AS check_name, COUNT(*) AS observed, 4 AS expected FROM orders;

-- Expected: all four original order/user pairs are present.
SELECT 'dependent_orders_preserved' AS check_name, COUNT(*) AS observed, 4 AS expected
FROM orders
WHERE (id, user_id) IN (('o1','u1'),('o2','u4'),('o3','u5'),('o4','u6'));

-- Expected cleaned values for dirty users.
SELECT id, email AS observed_email,
       CASE id WHEN 'u4' THEN 'ada+u4@example.com'
               WHEN 'u5' THEN 'missing+u5@example.invalid'
               WHEN 'u6' THEN 'missing+u6@example.invalid' END AS expected_email
FROM users WHERE id IN ('u4','u5','u6') ORDER BY id;

-- Expected: zero null/blank emails and zero duplicate email groups.
SELECT 'null_or_blank_emails' AS check_name, COUNT(*) AS observed, 0 AS expected
FROM users WHERE email IS NULL OR trim(email) = '';
SELECT 'duplicate_email_groups' AS check_name, COUNT(*) AS observed, 0 AS expected
FROM (SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1);

-- Expected: all status values are non-null and active.
SELECT 'invalid_status_rows' AS check_name, COUNT(*) AS observed, 0 AS expected
FROM users WHERE status IS NULL;
SELECT 'active_status_rows' AS check_name, COUNT(*) AS observed, 6 AS expected
FROM users WHERE status = 'active';

-- Structural checks: users must expose NOT NULL email/status and a UNIQUE email index.
PRAGMA table_info(users);
PRAGMA index_list(users);

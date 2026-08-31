PRAGMA foreign_keys = ON;

-- Each query returns the expected value (6, 4, and 0 respectively).
SELECT 'user_count' AS check_name, COUNT(*) AS observed, 6 AS expected FROM users;
SELECT 'order_count' AS check_name, COUNT(*) AS observed, 4 AS expected FROM orders;

-- No order may be lost or retargeted; this checks every original dependency.
WITH expected(id, user_id) AS (
    VALUES ('o1','u1'), ('o2','u4'), ('o3','u5'), ('o4','u6')
)
SELECT 'order_user_id_mismatches' AS check_name,
       COUNT(*) AS observed, 0 AS expected
FROM expected e
LEFT JOIN orders o ON o.id = e.id AND o.user_id = e.user_id
WHERE o.id IS NULL;

WITH expected(id, email) AS (
    VALUES ('u4','ada+u4@example.com'),
           ('u5','missing+u5@example.invalid'),
           ('u6','missing+u6@example.invalid')
)
SELECT 'dirty_email_mismatches' AS check_name,
       COUNT(*) AS observed, 0 AS expected
FROM expected e
LEFT JOIN users u ON u.id = e.id AND u.email = e.email
WHERE u.id IS NULL;

SELECT 'null_emails' AS check_name, COUNT(*) AS observed, 0 AS expected
FROM users WHERE email IS NULL;
SELECT 'blank_emails' AS check_name, COUNT(*) AS observed, 0 AS expected
FROM users WHERE trim(email) = '';
SELECT 'duplicate_emails' AS check_name, COUNT(*) - COUNT(DISTINCT email) AS observed, 0 AS expected
FROM users;
SELECT 'non_active_or_null_status' AS check_name, COUNT(*) AS observed, 0 AS expected
FROM users WHERE status IS NULL OR status <> 'active';

-- Inspect declared constraints without issuing writes that intentionally fail.
SELECT 'users_email_not_null' AS check_name,
       (SELECT "notnull" FROM pragma_table_info('users') WHERE name = 'email') AS observed,
       1 AS expected;
SELECT 'users_status_not_null' AS check_name,
       (SELECT "notnull" FROM pragma_table_info('users') WHERE name = 'status') AS observed,
       1 AS expected;
SELECT 'users_email_unique_constraint' AS check_name,
       CASE WHEN instr(
           (SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = 'users'),
           'email TEXT NOT NULL UNIQUE'
       ) > 0 THEN 1 ELSE 0 END AS observed,
       1 AS expected;
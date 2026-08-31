-- Row counts
SELECT 'user_row_count' AS check_name, COUNT(*) AS actual, 6 AS expected, COUNT(*) = 6 AS ok
FROM users;

SELECT 'order_row_count' AS check_name, COUNT(*) AS actual, 4 AS expected, COUNT(*) = 4 AS ok
FROM orders;

-- Dependent order preservation for dirty users
SELECT 'orders_for_u4' AS check_name, COUNT(*) AS actual, 1 AS expected, COUNT(*) = 1 AS ok
FROM orders
WHERE user_id = 'u4';

SELECT 'orders_for_u5' AS check_name, COUNT(*) AS actual, 1 AS expected, COUNT(*) = 1 AS ok
FROM orders
WHERE user_id = 'u5';

SELECT 'orders_for_u6' AS check_name, COUNT(*) AS actual, 1 AS expected, COUNT(*) = 1 AS ok
FROM orders
WHERE user_id = 'u6';

-- Dirty-user cleanup values
SELECT 'dirty_user_email_cleanup' AS check_name, id, email,
       CASE
           WHEN id = 'u4' AND email = 'ada+u4@example.com' THEN 1
           WHEN id = 'u5' AND email = 'missing+u5@example.invalid' THEN 1
           WHEN id = 'u6' AND email = 'missing+u6@example.invalid' THEN 1
           ELSE 0
       END AS ok
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- Data quality after cleanup
SELECT 'null_or_blank_emails' AS check_name, COUNT(*) AS actual, 0 AS expected, COUNT(*) = 0 AS ok
FROM users
WHERE email IS NULL OR trim(email) = '';

SELECT 'duplicate_emails' AS check_name, COUNT(*) AS actual, 0 AS expected, COUNT(*) = 0 AS ok
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT 'null_status_rows' AS check_name, COUNT(*) AS actual, 0 AS expected, COUNT(*) = 0 AS ok
FROM users
WHERE status IS NULL;

SELECT 'non_active_status_rows' AS check_name, COUNT(*) AS actual, 0 AS expected, COUNT(*) = 0 AS ok
FROM users
WHERE status <> 'active';

-- Schema checks
SELECT 'users_table_has_status_default' AS check_name,
       instr((SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'), "status TEXT NOT NULL DEFAULT 'active'") > 0 AS ok;

SELECT 'users_table_enforces_email_not_null' AS check_name,
       instr((SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'), 'email TEXT NOT NULL UNIQUE') > 0 AS ok;

SELECT 'users_table_rejects_blank_email' AS check_name,
       instr((SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'), 'CHECK (length(trim(email)) > 0)') > 0 AS ok;

PRAGMA foreign_key_check;

SELECT 'users_row_count' AS check_name, COUNT(*) AS actual, 6 AS expected, COUNT(*) = 6 AS ok
FROM users;

SELECT 'orders_row_count' AS check_name, COUNT(*) AS actual, 4 AS expected, COUNT(*) = 4 AS ok
FROM orders;

SELECT
    'dirty_user_email_cleanup' AS check_name,
    id,
    email,
    CASE
        WHEN id = 'u4' THEN email = 'ada+u4@example.com'
        WHEN id = 'u5' THEN email = 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN email = 'missing+u6@example.invalid'
    END AS ok
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT
    'dependent_orders_preserved' AS check_name,
    o.id AS order_id,
    o.user_id,
    u.email,
    u.status,
    (o.user_id = u.id) AS ok
FROM orders AS o
JOIN users AS u ON u.id = o.user_id
WHERE o.id IN ('o2', 'o3', 'o4')
ORDER BY o.id;

SELECT 'null_or_blank_emails' AS check_name, COUNT(*) AS violations, COUNT(*) = 0 AS ok
FROM users
WHERE email IS NULL OR trim(email) = '';

SELECT 'duplicate_emails' AS check_name, COUNT(*) AS duplicate_groups, COUNT(*) = 0 AS ok
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT 'null_or_blank_status' AS check_name, COUNT(*) AS violations, COUNT(*) = 0 AS ok
FROM users
WHERE status IS NULL OR trim(status) = '';

SELECT
    'users_status_column_definition' AS check_name,
    name,
    type,
    "notnull",
    dflt_value,
    (name = 'status' AND type = 'TEXT' AND "notnull" = 1 AND dflt_value = '''active''') AS ok
FROM pragma_table_info('users')
WHERE name = 'status';

SELECT
    'users_email_constraints_present' AS check_name,
    sql LIKE '%email TEXT NOT NULL UNIQUE%' AND sql LIKE '%CHECK (length(trim(email)) > 0)%' AS ok,
    sql
FROM sqlite_master
WHERE type = 'table' AND name = 'users';

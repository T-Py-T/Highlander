SELECT
    'user_row_count' AS check_name,
    COUNT(*) AS actual_count,
    6 AS expected_count,
    COUNT(*) = 6 AS ok
FROM users;

SELECT
    'order_row_count' AS check_name,
    COUNT(*) AS actual_count,
    4 AS expected_count,
    COUNT(*) = 4 AS ok
FROM orders;

SELECT
    'dependent_orders_preserved' AS check_name,
    o.id AS order_id,
    o.user_id,
    o.total_cents,
    u.email,
    o.user_id IN ('u4', 'u5', 'u6') AS ok
FROM orders AS o
JOIN users AS u
    ON u.id = o.user_id
WHERE o.id IN ('o2', 'o3', 'o4')
ORDER BY o.id;

SELECT
    'dirty_user_email_cleanup' AS check_name,
    id,
    email AS actual_email,
    CASE id
        WHEN 'u4' THEN 'ada+u4@example.com'
        WHEN 'u5' THEN 'missing+u5@example.invalid'
        WHEN 'u6' THEN 'missing+u6@example.invalid'
    END AS expected_email,
    email = CASE id
        WHEN 'u4' THEN 'ada+u4@example.com'
        WHEN 'u5' THEN 'missing+u5@example.invalid'
        WHEN 'u6' THEN 'missing+u6@example.invalid'
    END AS ok
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT
    'no_null_or_blank_emails' AS check_name,
    SUM(CASE WHEN email IS NULL OR TRIM(email) = '' THEN 1 ELSE 0 END) AS invalid_email_rows,
    SUM(CASE WHEN email IS NULL OR TRIM(email) = '' THEN 1 ELSE 0 END) = 0 AS ok
FROM users;

SELECT
    'unique_emails' AS check_name,
    COUNT(*) AS user_count,
    COUNT(DISTINCT email) AS distinct_email_count,
    COUNT(*) = COUNT(DISTINCT email) AS ok
FROM users;

SELECT
    'status_not_null' AS check_name,
    SUM(CASE WHEN status IS NULL THEN 1 ELSE 0 END) AS null_status_rows,
    SUM(CASE WHEN status IS NULL THEN 1 ELSE 0 END) = 0 AS ok
FROM users;

SELECT
    'status_default_active_present' AS check_name,
    EXISTS (
 SELECT 1
        FROM pragma_table_info('users')
        WHERE name = 'status'
          AND "notnull" = 1
          AND dflt_value = '''active'''
    ) AS ok;

SELECT
    'email_not_null_column' AS check_name,
    EXISTS (
 SELECT 1
        FROM pragma_table_info('users')
        WHERE name = 'email'
          AND "notnull" = 1
    ) AS ok;

SELECT
    'email_unique_constraint' AS check_name,
    EXISTS (
        SELECT 1
        FROM pragma_index_list('users') AS il
        JOIN pragma_index_info(il.name) AS ii
            ON 1 = 1
        WHERE il."unique" = 1
          AND ii.name = 'email'
    ) AS ok;

PRAGMA foreign_key_check;

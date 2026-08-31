-- Run after migration to verify data preservation, deterministic cleanup, and constraints.

SELECT
    'users_row_count' AS check_name,
    CASE WHEN COUNT(*) = 6 THEN 'PASS' ELSE 'FAIL' END AS result,
    COUNT(*) AS actual,
    6 AS expected
FROM users;

SELECT
    'orders_row_count' AS check_name,
    CASE WHEN COUNT(*) = 4 THEN 'PASS' ELSE 'FAIL' END AS result,
    COUNT(*) AS actual,
    4 AS expected
FROM orders;

SELECT
    'dirty_user_orders_preserved' AS check_name,
    CASE
        WHEN SUM(CASE WHEN id = 'o2' AND user_id = 'u4' THEN 1 ELSE 0 END) = 1
         AND SUM(CASE WHEN id = 'o3' AND user_id = 'u5' THEN 1 ELSE 0 END) = 1
         AND SUM(CASE WHEN id = 'o4' AND user_id = 'u6' THEN 1 ELSE 0 END) = 1
        THEN 'PASS' ELSE 'FAIL'
    END AS result,
    GROUP_CONCAT(id || ':' || user_id, ', ') AS observed_links,
    'o2:u4, o3:u5, o4:u6' AS expected_links
FROM orders
WHERE id IN ('o2', 'o3', 'o4');

SELECT
    'dirty_email_cleanup' AS check_name,
    CASE
        WHEN SUM(CASE WHEN id = 'u4' AND email = 'ada+u4@example.com' THEN 1 ELSE 0 END) = 1
         AND SUM(CASE WHEN id = 'u5' AND email = 'missing+u5@example.invalid' THEN 1 ELSE 0 END) = 1
         AND SUM(CASE WHEN id = 'u6' AND email = 'missing+u6@example.invalid' THEN 1 ELSE 0 END) = 1
        THEN 'PASS' ELSE 'FAIL'
    END AS result,
    GROUP_CONCAT(id || '=' || quote(email), ', ') AS observed_emails,
    'u4=ada+u4@example.com, u5=missing+u5@example.invalid, u6=missing+u6@example.invalid' AS expected_emails
FROM users
WHERE id IN ('u4', 'u5', 'u6');

SELECT
    'email_not_null_or_blank' AS check_name,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS result,
    COUNT(*) AS offending_rows,
    0 AS expected_offending_rows
FROM users
WHERE email IS NULL OR trim(email) = '';

SELECT
    'email_unique' AS check_name,
    CASE WHEN COUNT(DISTINCT email) = COUNT(*) THEN 'PASS' ELSE 'FAIL' END AS result,
    COUNT(DISTINCT email) AS distinct_emails,
    COUNT(*) AS user_rows
FROM users;

SELECT
    'status_column_shape' AS check_name,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM pragma_table_info('users')
            WHERE name = 'status'
              AND lower(type) = 'text'
              AND "notnull" = 1
              AND dflt_value = '''active'''
        )
        THEN 'PASS' ELSE 'FAIL'
    END AS result;

SELECT
    'status_values_present' AS check_name,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS result,
    COUNT(*) AS offending_rows,
    0 AS expected_offending_rows
FROM users
WHERE status IS NULL OR trim(status) = '';

SELECT
    'created_at_preserved_for_dirty_users' AS check_name,
    CASE
        WHEN SUM(CASE WHEN id = 'u4' AND created_at = '2023-12-01T08:00:00Z' THEN 1 ELSE 0 END) = 1
         AND SUM(CASE WHEN id = 'u5' AND created_at = '2023-11-05T12:00:00Z' THEN 1 ELSE 0 END) = 1
         AND SUM(CASE WHEN id = 'u6' AND created_at = '2023-10-06T07:45:00Z' THEN 1 ELSE 0 END) = 1
        THEN 'PASS' ELSE 'FAIL'
    END AS result
FROM users
WHERE id IN ('u4', 'u5', 'u6');

SELECT
    'foreign_key_check' AS check_name,
    CASE WHEN NOT EXISTS (SELECT 1 FROM pragma_foreign_key_check) THEN 'PASS' ELSE 'FAIL' END AS result;

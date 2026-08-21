SELECT 'users_row_count' AS check_name, COUNT(*) AS actual, 6 AS expected, COUNT(*) = 6 AS ok
FROM users;

SELECT 'orders_row_count' AS check_name, COUNT(*) AS actual, 4 AS expected, COUNT(*) = 4 AS ok
FROM orders;

SELECT 'order_user_refs_for_dirty_users' AS check_name,
       group_concat(id || ':' || user_id, ',') AS actual,
       'o2:u4,o3:u5,o4:u6' AS expected,
       group_concat(id || ':' || user_id, ',') = 'o2:u4,o3:u5,o4:u6' AS ok
FROM (
    SELECT id, user_id
    FROM orders
    WHERE user_id IN ('u4', 'u5', 'u6')
    ORDER BY id
);

SELECT 'dirty_user_email_cleanup' AS check_name,
       group_concat(id || ':' || email, ',') AS actual,
       'u4:ada+u4@example.com,u5:missing+u5@example.invalid,u6:missing+u6@example.invalid' AS expected,
       group_concat(id || ':' || email, ',') = 'u4:ada+u4@example.com,u5:missing+u5@example.invalid,u6:missing+u6@example.invalid' AS ok
FROM (
    SELECT id, email
    FROM users
    WHERE id IN ('u4', 'u5', 'u6')
    ORDER BY id
);

SELECT 'email_not_null_or_blank' AS check_name,
       COUNT(*) AS violations,
       0 AS expected,
       COUNT(*) = 0 AS ok
FROM users
WHERE email IS NULL OR TRIM(email) = '';

SELECT 'email_unique_values' AS check_name,
       COUNT(DISTINCT email) AS distinct_emails,
       COUNT(*) AS user_rows,
       COUNT(DISTINCT email) = COUNT(*) AS ok
FROM users;

SELECT 'status_backfill_active' AS check_name,
       COUNT(*) AS active_rows,
       6 AS expected,
       COUNT(*) = 6 AS ok
FROM users
WHERE status = 'active';

SELECT 'status_column_metadata' AS check_name,
       EXISTS (
           SELECT 1
           FROM pragma_table_info('users')
           WHERE name = 'status' AND type = 'TEXT' AND "notnull" = 1 AND dflt_value = '''active'''
       ) AS ok;

SELECT 'email_column_metadata' AS check_name,
       EXISTS (
           SELECT 1
           FROM pragma_table_info('users')
           WHERE name = 'email' AND type = 'TEXT' AND "notnull" = 1
       ) AS ok;

SELECT 'email_unique_index' AS check_name,
       COALESCE(MAX(is_email_unique), 0) AS ok
FROM (
    SELECT CASE
               WHEN il."unique" = 1 AND COUNT(*) = 1 AND MAX(ii.name = 'email') = 1 THEN 1
               ELSE 0
           END AS is_email_unique
    FROM pragma_index_list('users') AS il
    JOIN pragma_index_info(il.name) AS ii
    GROUP BY il.name
);

SELECT 'foreign_key_integrity' AS check_name,
       COUNT(*) AS violations,
       0 AS expected,
       COUNT(*) = 0 AS ok
FROM pragma_foreign_key_check;
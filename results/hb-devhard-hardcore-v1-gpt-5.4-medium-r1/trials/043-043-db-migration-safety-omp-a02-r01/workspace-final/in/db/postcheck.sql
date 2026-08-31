SELECT 'user_row_count' AS check_name,
       CASE WHEN (SELECT COUNT(*) FROM users) = 6 THEN 'PASS' ELSE 'FAIL' END AS result,
       (SELECT COUNT(*) FROM users) AS actual_count,
       6 AS expected_count;

SELECT 'order_row_count' AS check_name,
       CASE WHEN (SELECT COUNT(*) FROM orders) = 4 THEN 'PASS' ELSE 'FAIL' END AS result,
       (SELECT COUNT(*) FROM orders) AS actual_count,
       4 AS expected_count;

SELECT 'dirty_user_orders_preserved' AS check_name,
       CASE
           WHEN EXISTS (SELECT 1 FROM orders WHERE id = 'o2' AND user_id = 'u4')
            AND EXISTS (SELECT 1 FROM orders WHERE id = 'o3' AND user_id = 'u5')
            AND EXISTS (SELECT 1 FROM orders WHERE id = 'o4' AND user_id = 'u6')
           THEN 'PASS'
           ELSE 'FAIL'
       END AS result;

SELECT 'cleaned_dirty_emails' AS check_name,
       CASE
           WHEN EXISTS (SELECT 1 FROM users WHERE id = 'u4' AND email = 'ada+u4@example.com')
            AND EXISTS (SELECT 1 FROM users WHERE id = 'u5' AND email = 'missing+u5@example.invalid')
            AND EXISTS (SELECT 1 FROM users WHERE id = 'u6' AND email = 'missing+u6@example.invalid')
           THEN 'PASS'
           ELSE 'FAIL'
       END AS result;

SELECT 'email_not_null_or_blank' AS check_name,
       CASE
           WHEN EXISTS (SELECT 1 FROM users WHERE email IS NULL OR TRIM(email) = '')
           THEN 'FAIL'
           ELSE 'PASS'
       END AS result;

SELECT 'email_unique' AS check_name,
       CASE
           WHEN EXISTS (
               SELECT email
               FROM users
               GROUP BY email
               HAVING COUNT(*) > 1
           )
           THEN 'FAIL'
           ELSE 'PASS'
       END AS result;

SELECT 'status_all_active_and_non_null' AS check_name,
       CASE
           WHEN EXISTS (SELECT 1 FROM users WHERE status IS NULL OR status <> 'active')
           THEN 'FAIL'
           ELSE 'PASS'
       END AS result;

SELECT 'users_schema_has_status_not_null_default' AS check_name,
       CASE
           WHEN EXISTS (
               SELECT 1
               FROM pragma_table_info('users')
               WHERE name = 'status'
                 AND type = 'TEXT'
                 AND "notnull" = 1
                 AND dflt_value = '''active'''
           )
           THEN 'PASS'
           ELSE 'FAIL'
       END AS result;

SELECT 'users_schema_has_email_not_null' AS check_name,
       CASE
           WHEN EXISTS (
               SELECT 1
               FROM pragma_table_info('users')
               WHERE name = 'email'
                 AND type = 'TEXT'
                 AND "notnull" = 1
           )
           THEN 'PASS'
           ELSE 'FAIL'
       END AS result;

SELECT 'users_has_unique_email_index' AS check_name,
       CASE
           WHEN EXISTS (
               SELECT 1
               FROM pragma_index_list('users')
               WHERE name = 'idx_users_email'
                 AND "unique" = 1
           )
           THEN 'PASS'
           ELSE 'FAIL'
       END AS result;

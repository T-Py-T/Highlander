-- Post-migration verification queries. Each result should be 1 / true,
-- except the metadata PRAGMAs which expose the installed constraints.
PRAGMA foreign_keys = ON;

SELECT 'users_row_count' AS check_name,
       CASE WHEN COUNT(*) = 6 THEN 1 ELSE 0 END AS passed,
       COUNT(*) AS actual
FROM users;

SELECT 'orders_row_count' AS check_name,
       CASE WHEN COUNT(*) = 4 THEN 1 ELSE 0 END AS passed,
       COUNT(*) AS actual
FROM orders;

SELECT 'order_references_preserved' AS check_name,
       CASE WHEN COUNT(*) = 4
                 AND SUM(CASE WHEN id='o2' AND user_id='u4' THEN 1 ELSE 0 END)=1
                 AND SUM(CASE WHEN id='o3' AND user_id='u5' THEN 1 ELSE 0 END)=1
                 AND SUM(CASE WHEN id='o4' AND user_id='u6' THEN 1 ELSE 0 END)=1
            THEN 1 ELSE 0 END AS passed
FROM orders;

SELECT 'dirty_emails_cleaned' AS check_name,
       CASE WHEN (SELECT email FROM users WHERE id='u4')='ada+u4@example.com'
                  AND (SELECT email FROM users WHERE id='u5')='missing+u5@example.invalid'
                  AND (SELECT email FROM users WHERE id='u6')='missing+u6@example.invalid'
            THEN 1 ELSE 0 END AS passed;

SELECT 'all_emails_nonnull_nonblank_unique' AS check_name,
       CASE WHEN COUNT(*)=6
                  AND COUNT(email)=6
                  AND SUM(CASE WHEN trim(email)='' THEN 1 ELSE 0 END)=0
                  AND COUNT(DISTINCT email)=6
            THEN 1 ELSE 0 END AS passed
FROM users;

SELECT 'all_status_active_and_nonnull' AS check_name,
       CASE WHEN COUNT(*)=6 AND COUNT(status)=6
                  AND SUM(CASE WHEN status='active' THEN 1 ELSE 0 END)=6
            THEN 1 ELSE 0 END AS passed
FROM users;

-- Structural constraint checks: table_info reports NOT NULL, and the unique
-- index reports uniqueness. sqlite_master shows the complete table definition.
SELECT 'email_not_null_declared' AS check_name,
       CASE WHEN "notnull"=1 THEN 1 ELSE 0 END AS passed
FROM pragma_table_info('users') WHERE name='email';

SELECT 'status_not_null_declared' AS check_name,
       CASE WHEN "notnull"=1 AND dflt_value="'active'" THEN 1 ELSE 0 END AS passed
FROM pragma_table_info('users') WHERE name='status';

SELECT 'email_unique_declared' AS check_name,
       CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS passed
FROM pragma_index_list('users')
WHERE [unique]=1
  AND (name LIKE 'sqlite_autoindex_users_%' OR name LIKE '%email%');

SELECT sql AS users_table_definition
FROM sqlite_master
WHERE type='table' AND name='users';

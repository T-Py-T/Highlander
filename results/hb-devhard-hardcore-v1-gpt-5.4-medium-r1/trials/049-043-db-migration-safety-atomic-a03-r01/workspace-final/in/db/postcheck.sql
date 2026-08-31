-- Row counts must match the preserved pre-migration backup.
SELECT 'users_row_count_preserved' AS check_name,
       CASE WHEN (SELECT COUNT(*) FROM users) = (SELECT COUNT(*) FROM users__rollback_backup) THEN 'PASS' ELSE 'FAIL' END AS result,
       (SELECT COUNT(*) FROM users) AS users_count,
       (SELECT COUNT(*) FROM users__rollback_backup) AS backup_users_count;

SELECT 'orders_row_count_preserved' AS check_name,
       CASE WHEN (SELECT COUNT(*) FROM orders) = 4 THEN 'PASS' ELSE 'FAIL' END AS result,
       (SELECT COUNT(*) FROM orders) AS orders_count;

-- Orders for dirty users must still point at the same user ids.
SELECT 'dirty_user_order_refs_preserved' AS check_name,
       CASE WHEN EXISTS (SELECT 1 FROM orders WHERE id = 'o2' AND user_id = 'u4')
             AND EXISTS (SELECT 1 FROM orders WHERE id = 'o3' AND user_id = 'u5')
             AND EXISTS (SELECT 1 FROM orders WHERE id = 'o4' AND user_id = 'u6')
            THEN 'PASS' ELSE 'FAIL' END AS result;

SELECT 'no_orphan_order_refs' AS check_name,
       CASE WHEN NOT EXISTS (
           SELECT 1
           FROM orders o
           LEFT JOIN users u ON u.id = o.user_id
           WHERE u.id IS NULL
       ) THEN 'PASS' ELSE 'FAIL' END AS result;

-- Dirty rows must be cleaned to the required deterministic values.
SELECT 'dirty_user_email_cleanup' AS check_name,
       CASE WHEN EXISTS (SELECT 1 FROM users WHERE id = 'u4' AND email = 'ada+u4@example.com')
             AND EXISTS (SELECT 1 FROM users WHERE id = 'u5' AND email = 'missing+u5@example.invalid')
             AND EXISTS (SELECT 1 FROM users WHERE id = 'u6' AND email = 'missing+u6@example.invalid')
            THEN 'PASS' ELSE 'FAIL' END AS result;

-- Status and email rules must hold after migration.
SELECT 'status_column_present' AS check_name,
       CASE WHEN EXISTS (
           SELECT 1 FROM pragma_table_info('users')
           WHERE name = 'status' AND type = 'TEXT' AND "notnull" = 1 AND dflt_value = '''active'''
       ) THEN 'PASS' ELSE 'FAIL' END AS result;

SELECT 'all_status_values_present' AS check_name,
       CASE WHEN NOT EXISTS (SELECT 1 FROM users WHERE status IS NULL OR TRIM(status) = '')
            THEN 'PASS' ELSE 'FAIL' END AS result;

SELECT 'all_status_values_active' AS check_name,
       CASE WHEN NOT EXISTS (SELECT 1 FROM users WHERE status <> 'active')
            THEN 'PASS' ELSE 'FAIL' END AS result;

SELECT 'email_values_non_null_non_blank' AS check_name,
       CASE WHEN NOT EXISTS (SELECT 1 FROM users WHERE email IS NULL OR TRIM(email) = '')
            THEN 'PASS' ELSE 'FAIL' END AS result;

SELECT 'email_values_unique' AS check_name,
       CASE WHEN NOT EXISTS (
           SELECT email
           FROM users
           GROUP BY email
           HAVING COUNT(*) > 1
       ) THEN 'PASS' ELSE 'FAIL' END AS result;

SELECT 'email_unique_index_present' AS check_name,
       CASE WHEN EXISTS (
           SELECT 1
           FROM sqlite_master
           WHERE type = 'index'
             AND name = 'users_email_unique_idx'
             AND sql LIKE '%UNIQUE INDEX users_email_unique_idx ON users (email)%'
       ) THEN 'PASS' ELSE 'FAIL' END AS result;

SELECT 'email_reject_null_blank_triggers_present' AS check_name,
       CASE WHEN EXISTS (
           SELECT 1 FROM sqlite_master
           WHERE type = 'trigger' AND name = 'users_email_not_blank_insert'
       ) AND EXISTS (
           SELECT 1 FROM sqlite_master
           WHERE type = 'trigger' AND name = 'users_email_not_blank_update'
       ) THEN 'PASS' ELSE 'FAIL' END AS result;

SELECT 'user_row_count' AS check_name, COUNT(*) AS actual, 6 AS expected, COUNT(*) = 6 AS pass
FROM users;

SELECT 'order_row_count' AS check_name, COUNT(*) AS actual, 4 AS expected, COUNT(*) = 4 AS pass
FROM orders;

SELECT 'order_refs_for_dirty_users' AS check_name, COUNT(*) AS actual, 3 AS expected, COUNT(*) = 3 AS pass
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6');

SELECT 'dirty_user_orders' AS section, id, user_id, total_cents, created_at
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT 'cleaned_dirty_users' AS section, id, email, status, created_at
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT 'duplicate_email_groups' AS check_name, COUNT(*) AS actual, 0 AS expected, COUNT(*) = 0 AS pass
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT 'null_or_blank_emails' AS check_name, COUNT(*) AS actual, 0 AS expected, COUNT(*) = 0 AS pass
FROM users
WHERE email IS NULL OR TRIM(email) = '';

SELECT 'null_status_rows' AS check_name, COUNT(*) AS actual, 0 AS expected, COUNT(*) = 0 AS pass
FROM users
WHERE status IS NULL;

SELECT 'status_column_definition' AS check_name,
       COUNT(*) AS actual,
       1 AS expected,
       COUNT(*) = 1 AS pass
FROM pragma_table_info('users')
WHERE name = 'status'
  AND type = 'TEXT'
  AND "notnull" = 1
  AND dflt_value = '''active''';

SELECT 'email_unique_index_present' AS check_name,
       COUNT(*) AS actual,
       1 AS expected,
       COUNT(*) = 1 AS pass
FROM pragma_index_list('users')
WHERE name = 'users_email_unique'
  AND "unique" = 1;

SELECT 'email_required_insert_trigger_present' AS check_name,
       COUNT(*) AS actual,
       1 AS expected,
       COUNT(*) = 1 AS pass
FROM sqlite_master
WHERE type = 'trigger'
  AND name = 'users_email_required_insert';

SELECT 'email_required_update_trigger_present' AS check_name,
       COUNT(*) AS actual,
       1 AS expected,
       COUNT(*) = 1 AS pass
FROM sqlite_master
WHERE type = 'trigger'
  AND name = 'users_email_required_update';

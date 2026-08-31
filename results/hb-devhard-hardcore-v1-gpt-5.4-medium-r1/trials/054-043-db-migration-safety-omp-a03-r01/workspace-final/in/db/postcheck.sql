SELECT 'user_row_count' AS check_name, COUNT(*) AS actual_count, 6 AS expected_count, COUNT(*) = 6 AS ok
FROM users;

SELECT 'order_row_count' AS check_name, COUNT(*) AS actual_count, 4 AS expected_count, COUNT(*) = 4 AS ok
FROM orders;

SELECT 'dirty_user_order_count' AS check_name, COUNT(*) AS actual_count, 3 AS expected_count, COUNT(*) = 3 AS ok
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6');

SELECT 'dirty_user_orders' AS check_name, id AS order_id, user_id, total_cents, created_at
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT 'cleaned_dirty_emails' AS check_name, id, email,
       CASE
           WHEN id = 'u4' THEN email = 'ada+u4@example.com'
           WHEN id = 'u5' THEN email = 'missing+u5@example.invalid'
           WHEN id = 'u6' THEN email = 'missing+u6@example.invalid'
       END AS ok
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT 'null_or_blank_email_rows' AS check_name, COUNT(*) AS actual_count, 0 AS expected_count, COUNT(*) = 0 AS ok
FROM users
WHERE email IS NULL OR trim(email) = '';

SELECT 'duplicate_email_groups' AS check_name, COUNT(*) AS actual_count, 0 AS expected_count, COUNT(*) = 0 AS ok
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT 'status_defaulted_active' AS check_name, COUNT(*) AS actual_count, 6 AS expected_count, COUNT(*) = 6 AS ok
FROM users
WHERE status = 'active';

SELECT 'status_column_definition' AS check_name, name, type, "notnull", dflt_value,
       (type = 'TEXT' AND "notnull" = 1 AND dflt_value = '''active''') AS ok
FROM pragma_table_info('users')
WHERE name = 'status';

SELECT 'email_column_not_null' AS check_name, name, "notnull", "notnull" = 1 AS ok
FROM pragma_table_info('users')
WHERE name = 'email';

SELECT 'email_unique_index_present' AS check_name, COUNT(*) AS actual_count, COUNT(*) >= 1 AS ok
FROM pragma_index_list('users')
WHERE "unique" = 1
  AND name IN (
      SELECT il.name
      FROM pragma_index_list('users') AS il
      JOIN pragma_index_info(il.name) AS ii ON 1 = 1
      WHERE ii.name = 'email'
  );

SELECT 'created_at_preserved_for_dirty_users' AS check_name, id, created_at,
       CASE
           WHEN id = 'u4' THEN created_at = '2023-12-01T08:00:00Z'
           WHEN id = 'u5' THEN created_at = '2023-11-05T12:00:00Z'
           WHEN id = 'u6' THEN created_at = '2023-10-06T07:45:00Z'
       END AS ok
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT 'user_row_count' AS check_name, COUNT(*) AS actual, 6 AS expected
FROM users;

SELECT 'order_row_count' AS check_name, COUNT(*) AS actual, 4 AS expected
FROM orders;

SELECT id, email, status, created_at
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT id, user_id, total_cents, created_at
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT 'invalid_email_or_status_rows' AS check_name, COUNT(*) AS invalid_rows
FROM users
WHERE email IS NULL OR TRIM(email) = '' OR status IS NULL OR TRIM(status) = '';

SELECT 'duplicate_email_rows' AS check_name, COUNT(*) AS duplicate_groups
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT name, "notnull" AS is_not_null, dflt_value
FROM pragma_table_info('users')
WHERE name IN ('email', 'status')
ORDER BY name;

SELECT il.name AS index_name, il."unique" AS is_unique
FROM pragma_index_list('users') AS il
WHERE il."unique" = 1
  AND EXISTS (
      SELECT 1
      FROM pragma_index_info(il.name) AS ii
      WHERE ii.name = 'email'
  );

SELECT *
FROM pragma_foreign_key_check;

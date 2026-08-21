SELECT 'users_row_count' AS check_name,
       CASE WHEN (SELECT COUNT(*) FROM users) = 6 THEN 'ok' ELSE 'fail' END AS result,
       (SELECT COUNT(*) FROM users) AS actual,
       6 AS expected;

SELECT 'orders_row_count' AS check_name,
       CASE WHEN (SELECT COUNT(*) FROM orders) = 4 THEN 'ok' ELSE 'fail' END AS result,
       (SELECT COUNT(*) FROM orders) AS actual,
       4 AS expected;

WITH expected(user_id, expected_count) AS (
    VALUES ('u4', 1), ('u5', 1), ('u6', 1)
),
actual AS (
    SELECT user_id, COUNT(*) AS actual_count
    FROM orders
    WHERE user_id IN ('u4', 'u5', 'u6')
    GROUP BY user_id
)
SELECT 'dirty_user_order_counts' AS check_name,
       CASE WHEN NOT EXISTS (
           SELECT 1
           FROM expected
           LEFT JOIN actual USING (user_id)
           WHERE COALESCE(actual.actual_count, 0) <> expected.expected_count
       ) THEN 'ok' ELSE 'fail' END AS result,
       (SELECT group_concat(user_id || ':' || order_ids, ',')
        FROM (
            SELECT user_id, group_concat(id, '|') AS order_ids
            FROM orders
            WHERE user_id IN ('u4', 'u5', 'u6')
            GROUP BY user_id
            ORDER BY user_id
        )) AS actual,
       'u4:o2,u5:o3,u6:o4' AS expected;

WITH expected(id, expected_email) AS (
    VALUES
        ('u4', 'ada+u4@example.com'),
        ('u5', 'missing+u5@example.invalid'),
        ('u6', 'missing+u6@example.invalid')
)
SELECT 'dirty_user_emails' AS check_name,
       CASE WHEN NOT EXISTS (
           SELECT 1
           FROM expected
           JOIN users ON users.id = expected.id
           WHERE users.email <> expected.expected_email
       ) THEN 'ok' ELSE 'fail' END AS result,
       (SELECT group_concat(id || ':' || email, ',')
        FROM (
            SELECT id, email
            FROM users
            WHERE id IN ('u4', 'u5', 'u6')
            ORDER BY id
        )) AS actual,
       'u4:ada+u4@example.com,u5:missing+u5@example.invalid,u6:missing+u6@example.invalid' AS expected;

WITH expected(id, expected_created_at) AS (
    VALUES
        ('u1', '2024-01-02T10:00:00Z'),
        ('u2', '2024-02-03T11:30:00Z'),
        ('u3', '2024-03-04T09:15:00Z'),
        ('u4', '2023-12-01T08:00:00Z'),
        ('u5', '2023-11-05T12:00:00Z'),
        ('u6', '2023-10-06T07:45:00Z')
)
SELECT 'created_at_preserved' AS check_name,
       CASE WHEN NOT EXISTS (
           SELECT 1
           FROM expected
           JOIN users ON users.id = expected.id
           WHERE users.created_at <> expected.expected_created_at
       ) THEN 'ok' ELSE 'fail' END AS result,
       (SELECT group_concat(id || ':' || created_at, ',')
        FROM (
            SELECT id, created_at
            FROM users
            ORDER BY id
        )) AS actual,
       'original created_at values preserved' AS expected;

SELECT 'email_not_null_column' AS check_name,
       CASE WHEN EXISTS (
           SELECT 1
           FROM pragma_table_info('users')
           WHERE name = 'email' AND "notnull" = 1
       ) THEN 'ok' ELSE 'fail' END AS result,
       (SELECT "notnull" FROM pragma_table_info('users') WHERE name = 'email') AS actual,
       1 AS expected;

SELECT 'status_column_definition' AS check_name,
       CASE WHEN EXISTS (
           SELECT 1
           FROM pragma_table_info('users')
           WHERE name = 'status' AND "notnull" = 1 AND dflt_value = '''active'''
       ) THEN 'ok' ELSE 'fail' END AS result,
       (SELECT COALESCE(CAST("notnull" AS TEXT), '0') || ':' || COALESCE(dflt_value, 'NULL')
        FROM pragma_table_info('users')
        WHERE name = 'status') AS actual,
       '1:''active''' AS expected;

SELECT 'email_unique_constraint' AS check_name,
       CASE WHEN EXISTS (
           SELECT 1
           FROM pragma_index_list('users') AS il
           JOIN pragma_index_info(il.name) AS ii
           GROUP BY il.name
           HAVING MAX(il."unique") = 1
              AND COUNT(*) = 1
              AND SUM(CASE WHEN ii.name = 'email' THEN 1 ELSE 0 END) = 1
       ) THEN 'ok' ELSE 'fail' END AS result,
       (SELECT group_concat(il.name, ',')
        FROM pragma_index_list('users') AS il
        WHERE il."unique" = 1) AS actual,
       'single-column unique index on email' AS expected;

SELECT 'email_values_clean' AS check_name,
       CASE WHEN (
           SELECT COUNT(*)
           FROM users
           WHERE email IS NULL OR TRIM(email) = ''
       ) = 0 THEN 'ok' ELSE 'fail' END AS result,
       (SELECT COUNT(*) FROM users WHERE email IS NULL OR TRIM(email) = '') AS actual,
       0 AS expected;

SELECT 'email_values_distinct' AS check_name,
       CASE WHEN (
           SELECT COUNT(*) FROM users
       ) = (
           SELECT COUNT(DISTINCT email) FROM users
       ) THEN 'ok' ELSE 'fail' END AS result,
       (SELECT COUNT(DISTINCT email) FROM users) AS actual,
       (SELECT COUNT(*) FROM users) AS expected;

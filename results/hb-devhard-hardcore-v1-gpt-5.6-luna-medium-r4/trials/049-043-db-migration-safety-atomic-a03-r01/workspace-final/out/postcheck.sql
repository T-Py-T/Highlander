WITH checks (check_name, passed, details) AS (
    SELECT
        'users_row_count',
        (SELECT COUNT(*) FROM users) = 6,
        'expected=6 actual=' || (SELECT COUNT(*) FROM users)
    UNION ALL
    SELECT
        'orders_row_count',
        (SELECT COUNT(*) FROM orders) = 4,
        'expected=4 actual=' || (SELECT COUNT(*) FROM orders)
    UNION ALL
    SELECT
        'dirty_user_dependencies',
        (SELECT COUNT(*)
         FROM orders
         WHERE (id = 'o2' AND user_id = 'u4')
            OR (id = 'o3' AND user_id = 'u5')
            OR (id = 'o4' AND user_id = 'u6')) = 3,
        'expected=o2/u4,o3/u5,o4/u6'
    UNION ALL
    SELECT
        'cleaned_emails',
        (SELECT COUNT(*)
         FROM users
         WHERE (id = 'u1' AND email = 'ada@example.com')
            OR (id = 'u4' AND email = 'ada+u4@example.com')
            OR (id = 'u5' AND email = 'missing+u5@example.invalid')
            OR (id = 'u6' AND email = 'missing+u6@example.invalid')) = 4,
        'expected exact emails for u1,u4,u5,u6'
    UNION ALL
    SELECT
        'email_not_null',
        EXISTS (
            SELECT 1
            FROM pragma_table_info('users')
            WHERE name = 'email' AND "notnull" = 1
        ),
        'expected users.email NOT NULL'
    UNION ALL
    SELECT
        'email_unique',
        EXISTS (
            SELECT 1
            FROM pragma_index_list('users') AS indexes
            WHERE indexes."unique" = 1
              AND (SELECT COUNT(*) FROM pragma_index_info(indexes.name)) = 1
              AND (SELECT name FROM pragma_index_info(indexes.name) LIMIT 1) = 'email'
        ),
        'expected a single-column UNIQUE index on users.email'
    UNION ALL
    SELECT
        'status_schema',
        EXISTS (
            SELECT 1
            FROM pragma_table_info('users')
            WHERE name = 'status'
              AND type = 'TEXT'
              AND "notnull" = 1
              AND dflt_value = '''active'''
        ),
        'expected status TEXT NOT NULL DEFAULT active'
    UNION ALL
    SELECT
        'migrated_status_values',
        (SELECT COUNT(*) FROM users) = 6
            AND (SELECT COUNT(*) FROM users WHERE status = 'active') = 6,
        'expected all 6 migrated users to have status=active'
    UNION ALL
    SELECT
        'foreign_key_integrity',
        NOT EXISTS (SELECT 1 FROM pragma_foreign_key_check),
        'expected no foreign key violations'
)
SELECT check_name, passed, details
FROM checks
ORDER BY check_name;

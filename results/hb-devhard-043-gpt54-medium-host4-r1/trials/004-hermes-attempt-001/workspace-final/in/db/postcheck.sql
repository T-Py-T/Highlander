PRAGMA foreign_keys = ON;

SELECT 'users_row_count' AS check_name, COUNT(*) = 6 AS ok, COUNT(*) AS actual, 6 AS expected
FROM users;

SELECT 'orders_row_count' AS check_name, COUNT(*) = 4 AS ok, COUNT(*) AS actual, 4 AS expected
FROM orders;

SELECT 'orders_preserved_for_u4_u5_u6' AS check_name,
       SUM(CASE WHEN user_id = 'u4' THEN 1 ELSE 0 END) = 1
       AND SUM(CASE WHEN user_id = 'u5' THEN 1 ELSE 0 END) = 1
       AND SUM(CASE WHEN user_id = 'u6' THEN 1 ELSE 0 END) = 1 AS ok,
       GROUP_CONCAT(id || ':' || user_id, ', ') AS actual,
       'o2:u4, o3:u5, o4:u6 present' AS expected
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6');

SELECT 'dirty_user_emails_cleaned' AS check_name,
       SUM(CASE WHEN id = 'u4' AND email = 'ada+u4@example.com' THEN 1 ELSE 0 END) = 1
       AND SUM(CASE WHEN id = 'u5' AND email = 'missing+u5@example.invalid' THEN 1 ELSE 0 END) = 1
       AND SUM(CASE WHEN id = 'u6' AND email = 'missing+u6@example.invalid' THEN 1 ELSE 0 END) = 1 AS ok,
       GROUP_CONCAT(id || ':' || email, ', ') AS actual,
       'u4/u5/u6 migrated to deterministic cleaned addresses' AS expected
FROM users
WHERE id IN ('u4', 'u5', 'u6');

SELECT 'created_at_preserved_for_dirty_users' AS check_name,
       SUM(CASE WHEN id = 'u4' AND created_at = '2023-12-01T08:00:00Z' THEN 1 ELSE 0 END) = 1
       AND SUM(CASE WHEN id = 'u5' AND created_at = '2023-11-05T12:00:00Z' THEN 1 ELSE 0 END) = 1
       AND SUM(CASE WHEN id = 'u6' AND created_at = '2023-10-06T07:45:00Z' THEN 1 ELSE 0 END) = 1 AS ok,
       GROUP_CONCAT(id || ':' || created_at, ', ') AS actual,
       'historical created_at values preserved' AS expected
FROM users
WHERE id IN ('u4', 'u5', 'u6');

SELECT 'email_values_are_now_present_and_unique' AS check_name,
       (SELECT COUNT(*) FROM users WHERE email IS NULL OR trim(email) = '') = 0
       AND (SELECT COUNT(*) FROM users) = (SELECT COUNT(DISTINCT email) FROM users) AS ok,
       (SELECT GROUP_CONCAT(id || ':' || COALESCE(quote(email), 'NULL'), ', ')
          FROM users
         WHERE email IS NULL OR trim(email) = '') AS actual,
       'no NULL or blank emails; all email values unique' AS expected;

SELECT 'email_column_is_not_null' AS check_name,
       EXISTS(
           SELECT 1
           FROM pragma_table_info('users')
           WHERE name = 'email' AND "notnull" = 1
       ) AS ok,
       (SELECT "notnull" FROM pragma_table_info('users') WHERE name = 'email') AS actual,
       1 AS expected;

SELECT 'status_column_has_not_null_and_default_active' AS check_name,
       EXISTS(
           SELECT 1
           FROM pragma_table_info('users')
            WHERE name = 'status'
             AND "notnull" = 1
             AND replace(dflt_value, '''', '') = 'active'
       ) AS ok,
       (SELECT 'notnull=' || "notnull" || ', default=' || COALESCE(dflt_value, 'NULL')
          FROM pragma_table_info('users')
         WHERE name = 'status') AS actual,
       'notnull=1, default=''active''' AS expected;

SELECT 'users_table_declares_unique_email_and_status' AS check_name,
       sql LIKE '%email TEXT NOT NULL UNIQUE CHECK (trim(email) <> '''')%'
       AND sql LIKE '%status TEXT NOT NULL DEFAULT ''active''%' AS ok,
       sql AS actual,
       'users table SQL includes email uniqueness/nonblank and status default' AS expected
FROM sqlite_master
WHERE type = 'table'
  AND name = 'users';

PRAGMA foreign_key_check;

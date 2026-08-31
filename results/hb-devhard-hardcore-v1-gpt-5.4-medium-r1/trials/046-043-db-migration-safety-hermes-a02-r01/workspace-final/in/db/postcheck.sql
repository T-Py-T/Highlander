-- Row preservation
SELECT 'users_row_count' AS check_name, COUNT(*) AS actual, 6 AS expected
FROM users;

SELECT 'orders_row_count' AS check_name, COUNT(*) AS actual, 4 AS expected
FROM orders;

-- Dependent order preservation for dirty users
SELECT 'dirty_user_order_refs' AS check_name, user_id, COUNT(*) AS order_count
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
GROUP BY user_id
ORDER BY user_id;

-- Deterministic dirty-email cleanup verification
SELECT 'cleaned_dirty_users' AS check_name, id, email, status, created_at
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- Historical created_at preservation spot-check for legacy dirty users
SELECT 'created_at_preserved' AS check_name, id, created_at
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- Constraint verification through schema inspection
SELECT 'users_columns' AS check_name, name, type, "notnull", dflt_value, pk
FROM pragma_table_info('users')
ORDER BY cid;

SELECT 'users_indexes' AS check_name, name, "unique", origin, partial
FROM pragma_index_list('users')
ORDER BY name;

-- Constraint-oriented data checks
SELECT 'null_or_blank_email_rows' AS check_name, COUNT(*) AS violating_rows
FROM users
WHERE email IS NULL OR trim(email) = '';

SELECT 'duplicate_email_groups' AS check_name, COUNT(*) AS violating_groups
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
);

SELECT 'null_status_rows' AS check_name, COUNT(*) AS violating_rows
FROM users
WHERE status IS NULL;

SELECT 'non_active_status_default_check' AS check_name, id, status
FROM users
ORDER BY id;

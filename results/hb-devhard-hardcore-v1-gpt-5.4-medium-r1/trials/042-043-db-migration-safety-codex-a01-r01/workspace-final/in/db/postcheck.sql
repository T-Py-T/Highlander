-- Row counts should match the legacy dataset.
SELECT 'users_row_count' AS check_name, COUNT(*) AS actual_count
FROM users;

SELECT 'orders_row_count' AS check_name, COUNT(*) AS actual_count
FROM orders;

-- Dirty users must still exist with the cleaned deterministic email values.
SELECT id, email, status, created_at
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

-- Dependent orders for dirty users must still point at the same user ids.
SELECT id, user_id, total_cents, created_at
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
ORDER BY user_id, id;

-- No null, blank, or duplicate emails should remain.
SELECT 'null_or_blank_email_rows' AS check_name, COUNT(*) AS issue_count
FROM users
WHERE email IS NULL OR trim(email) = '';

SELECT email, COUNT(*) AS duplicate_count
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

-- Status must be present for every row and default to active in migrated data.
SELECT status, COUNT(*) AS row_count
FROM users
GROUP BY status
ORDER BY status;

SELECT 'null_or_blank_status_rows' AS check_name, COUNT(*) AS issue_count
FROM users
WHERE status IS NULL OR trim(status) = '';

-- Returns zero rows when all order references remain valid.
PRAGMA foreign_key_check;

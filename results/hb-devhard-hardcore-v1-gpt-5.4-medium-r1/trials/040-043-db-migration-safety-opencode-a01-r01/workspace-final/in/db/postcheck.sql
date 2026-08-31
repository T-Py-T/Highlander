-- Row counts should remain unchanged.
SELECT COUNT(*) AS user_count FROM users;
SELECT COUNT(*) AS order_count FROM orders;

-- Dependent orders for dirty users must still point to the same user ids.
SELECT id, user_id, total_cents, created_at
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT user_id, COUNT(*) AS order_count
FROM orders
WHERE user_id IN ('u4', 'u5', 'u6')
GROUP BY user_id
ORDER BY user_id;

-- Cleaned emails and preserved timestamps for the dirty users.
SELECT id, email, status, created_at
FROM users
WHERE id IN ('u4', 'u5', 'u6')
ORDER BY id;

SELECT COUNT(*) AS cleaned_dirty_user_email_match_count
FROM users
WHERE (id = 'u4' AND email = 'ada+u4@example.com')
   OR (id = 'u5' AND email = 'missing+u5@example.invalid')
   OR (id = 'u6' AND email = 'missing+u6@example.invalid');

-- No null or blank emails should remain.
SELECT COUNT(*) AS null_or_blank_email_count
FROM users
WHERE email IS NULL OR trim(email) = '';

-- No duplicate emails should remain.
SELECT email, COUNT(*) AS duplicate_count
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

-- Status must be present for every row.
SELECT COUNT(*) AS null_or_blank_status_count
FROM users
WHERE status IS NULL OR trim(status) = '';

-- Schema check for the migrated users table.
PRAGMA table_info(users);

-- Foreign key references should still be valid after the rebuild.
PRAGMA foreign_key_check;

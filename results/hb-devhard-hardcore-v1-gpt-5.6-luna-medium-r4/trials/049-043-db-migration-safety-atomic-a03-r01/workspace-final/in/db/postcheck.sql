-- Each result should be 0 (no violation), except the two count queries which
-- should each return 6 and 4 respectively.
SELECT COUNT(*) AS user_count FROM users;
SELECT COUNT(*) AS order_count FROM orders;

-- No order was lost or retargeted; these are the expected dirty-user links.
SELECT COUNT(*) AS missing_dirty_user_orders
FROM (SELECT 'u4' AS user_id, 'o2' AS order_id
      UNION ALL SELECT 'u5', 'o3'
      UNION ALL SELECT 'u6', 'o4') expected
WHERE NOT EXISTS (
    SELECT 1 FROM orders o
    WHERE o.id = expected.order_id AND o.user_id = expected.user_id
);

SELECT COUNT(*) AS cleaned_email_violations
FROM (SELECT 'u4' AS id, 'ada+u4@example.com' AS email
      UNION ALL SELECT 'u5', 'missing+u5@example.invalid'
      UNION ALL SELECT 'u6', 'missing+u6@example.invalid') expected
JOIN users u ON u.id = expected.id
WHERE u.email <> expected.email;

SELECT COUNT(*) AS null_email_violations FROM users WHERE email IS NULL;
SELECT COUNT(*) AS blank_email_violations FROM users WHERE trim(email) = '';
SELECT COUNT(*) AS duplicate_email_violations
FROM users a JOIN users b ON a.email = b.email AND a.id < b.id;
SELECT COUNT(*) AS null_status_violations FROM users WHERE status IS NULL;
SELECT COUNT(*) AS inactive_default_violations FROM users WHERE status <> 'active';

-- Constraint probes: each INSERT must fail with a NOT NULL or UNIQUE error.
-- Run these manually in a transaction and ROLLBACK afterward:
-- INSERT INTO users(id,email,name,created_at) VALUES ('__postcheck_null__',NULL,'x','x');
-- INSERT INTO users(id,email,name,created_at) VALUES ('__postcheck_dup__','ada@example.com','x','x');

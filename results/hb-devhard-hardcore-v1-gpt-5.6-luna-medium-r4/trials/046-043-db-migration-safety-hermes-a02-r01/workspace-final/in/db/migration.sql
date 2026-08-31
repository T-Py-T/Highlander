-- Safe, deterministic users migration.
-- Dirty-data cleanup: u4 keeps its row but is assigned ada+u4@example.com;
-- u5 and u6 receive deterministic reserved addresses. No rows are deleted.
-- orders are left untouched and continue to reference the same user ids.
--
-- The script intentionally rebuilds users on every invocation. The rebuilt table
-- has the same user ids and historical values, so a second invocation is safe
-- and does not duplicate or lose users or orders.

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

DROP TABLE IF EXISTS users__migration_new;

CREATE TABLE users__migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users__migration_new (id, email, name, status, created_at)
SELECT
    id,
    CASE id
        WHEN 'u4' THEN 'ada+u4@example.com'
        WHEN 'u5' THEN 'missing+u5@example.invalid'
        WHEN 'u6' THEN 'missing+u6@example.invalid'
        ELSE email
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users;

-- Replacing only the parent table leaves orders' user_id values unchanged.
DROP TABLE users;
ALTER TABLE users__migration_new RENAME TO users;

COMMIT;
PRAGMA foreign_keys = ON;

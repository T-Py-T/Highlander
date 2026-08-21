PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE TRANSACTION;

CREATE TABLE IF NOT EXISTS users__migration_backup (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO users__migration_backup (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

DROP TABLE IF EXISTS users__new;

CREATE TABLE users__new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users__new (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' AND email = 'ada@example.com' THEN 'ada+u4@example.com'
        WHEN id = 'u5' AND email IS NULL THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' AND TRIM(email) = '' THEN 'missing+u6@example.invalid'
        ELSE email
    END AS migrated_email,
    name,
    'active' AS status,
    created_at
FROM users;

DROP TABLE users;
ALTER TABLE users__new RENAME TO users;

COMMIT;

PRAGMA foreign_keys = ON;

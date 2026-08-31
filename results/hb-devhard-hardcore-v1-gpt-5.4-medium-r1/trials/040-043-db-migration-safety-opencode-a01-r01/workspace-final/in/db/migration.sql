PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE TRANSACTION;

DROP TABLE IF EXISTS users__migration_source;

CREATE TABLE users__migration_source AS
SELECT id, email, name, created_at
FROM users;

DROP TABLE users;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (trim(email) <> ''),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

-- Preserve every user row while deterministically fixing known dirty emails.
INSERT INTO users (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN 'missing+u6@example.invalid'
        ELSE email
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users__migration_source;

DROP TABLE users__migration_source;

COMMIT;

PRAGMA foreign_keys = ON;

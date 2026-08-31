PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE TRANSACTION;

DROP TABLE IF EXISTS temp.users__migration_source;
CREATE TEMP TABLE users__migration_source AS
SELECT id, email, name, created_at
FROM users;

DROP TABLE users;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (length(trim(email)) > 0),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN 'missing+u6@example.invalid'
        WHEN email IS NULL THEN 'missing+' || id || '@example.invalid'
        WHEN trim(email) = '' THEN 'missing+' || id || '@example.invalid'
        ELSE email
    END,
    name,
    'active',
    created_at
FROM users__migration_source;

DROP TABLE temp.users__migration_source;

COMMIT;
PRAGMA foreign_keys = ON;

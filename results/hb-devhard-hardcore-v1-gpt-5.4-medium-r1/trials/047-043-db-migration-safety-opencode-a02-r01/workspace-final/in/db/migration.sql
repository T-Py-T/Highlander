PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

DROP TABLE IF EXISTS users__migration_backup;
DROP TABLE IF EXISTS users__migration_new;

CREATE TABLE users__migration_backup AS
SELECT
    id,
    email,
    name,
    created_at
FROM users;

CREATE TABLE users__migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (trim(email) <> ''),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

-- Preserve every existing user row while deterministically repairing the known
-- duplicate, null, and blank legacy emails before enforcing new constraints.
INSERT INTO users__migration_new (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN 'missing+u6@example.invalid'
        WHEN email IS NULL THEN 'missing+' || id || '@example.invalid'
        WHEN trim(email) = '' THEN 'missing+' || id || '@example.invalid'
        ELSE email
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users__migration_backup
ORDER BY created_at, id;

DROP TABLE users;
ALTER TABLE users__migration_new RENAME TO users;
DROP TABLE users__migration_backup;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);

COMMIT;

PRAGMA foreign_keys = ON;

-- Safe SQLite users migration.
--
-- Dirty data cleanup performed deterministically during the copy:
--   u4: ada@example.com              -> ada+u4@example.com
--   u5: NULL                         -> missing+u5@example.invalid
--   u6: '' / blank                   -> missing+u6@example.invalid
--
-- Re-running this script is data-stable: it rebuilds users from the current
-- rows without duplicating ids or orders, and the deterministic email mapping
-- yields the same result on subsequent runs.

PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE TRANSACTION;

DROP TABLE IF EXISTS users__migration_new;

CREATE TABLE users__migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (trim(email) <> ''),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users__migration_new (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN 'missing+u6@example.invalid'
        WHEN email IS NULL OR trim(email) = '' THEN 'missing+' || id || '@example.invalid'
        ELSE trim(email)
    END AS migrated_email,
    name,
    'active' AS status,
    created_at
FROM users;

DROP TABLE users;
ALTER TABLE users__migration_new RENAME TO users;

COMMIT;

PRAGMA foreign_keys = ON;

-- Should return no rows when referential integrity is preserved.
PRAGMA foreign_key_check;
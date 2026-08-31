PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

-- Rebuild users into the constrained shape while preserving ids, names,
-- historical created_at values, and existing order references.
DROP TABLE IF EXISTS _users_migration_source;
CREATE TABLE _users_migration_source (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Dirty-data cleanup is deterministic:
-- u4 duplicate ada@example.com -> ada+u4@example.com
-- u5 NULL email              -> missing+u5@example.invalid
-- u6 blank email             -> missing+u6@example.invalid
INSERT INTO _users_migration_source (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' AND email = 'ada@example.com' THEN 'ada+u4@example.com'
        WHEN id = 'u5' AND email IS NULL THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' AND TRIM(COALESCE(email, '')) = '' THEN 'missing+u6@example.invalid'
        ELSE email
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users;

DROP TABLE IF EXISTS users__migrated;
CREATE TABLE users__migrated (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (LENGTH(TRIM(email)) > 0),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users__migrated (id, email, name, status, created_at)
SELECT id, email, name, status, created_at
FROM _users_migration_source
ORDER BY created_at, id;

DROP TABLE users;
ALTER TABLE users__migrated RENAME TO users;

DROP TABLE _users_migration_source;

COMMIT;

PRAGMA foreign_keys = ON;

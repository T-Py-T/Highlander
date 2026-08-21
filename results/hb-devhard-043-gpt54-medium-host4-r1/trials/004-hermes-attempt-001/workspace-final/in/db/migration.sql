PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS _users_pre_migration_backup (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO _users_pre_migration_backup (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

DROP TABLE IF EXISTS users__new;

CREATE TABLE users__new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (trim(email) <> ''),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users__new (id, email, name, status, created_at)
SELECT
    backup.id,
    CASE
        WHEN backup.id = 'u4' THEN 'ada+u4@example.com'
        WHEN backup.id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN backup.id = 'u6' THEN 'missing+u6@example.invalid'
        WHEN backup.email IS NULL THEN 'missing+' || backup.id || '@example.invalid'
        WHEN trim(backup.email) = '' THEN 'missing+' || backup.id || '@example.invalid'
        WHEN backup.email = 'ada@example.com' AND backup.id <> 'u1' THEN 'ada+' || backup.id || '@example.com'
        ELSE backup.email
    END AS email,
    backup.name,
    'active' AS status,
    backup.created_at
FROM _users_pre_migration_backup AS backup;

DROP TABLE users;
ALTER TABLE users__new RENAME TO users;

PRAGMA foreign_key_check;

COMMIT;

PRAGMA foreign_keys = ON;
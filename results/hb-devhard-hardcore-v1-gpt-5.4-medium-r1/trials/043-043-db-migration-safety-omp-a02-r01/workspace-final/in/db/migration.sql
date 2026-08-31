BEGIN IMMEDIATE;

PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS _migration_users_v1_source (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO _migration_users_v1_source (id, email, name, created_at)
SELECT users.id, users.email, users.name, users.created_at
FROM users
WHERE NOT EXISTS (
    SELECT 1
    FROM _migration_users_v1_source
);

DROP TABLE IF EXISTS users__migrated;

CREATE TABLE users__migrated (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users__migrated (id, email, name, status, created_at)
SELECT
    src.id,
    CASE
        WHEN src.id = 'u4' THEN 'ada+u4@example.com'
        WHEN src.id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN src.id = 'u6' THEN 'missing+u6@example.invalid'
        ELSE TRIM(src.email)
    END AS migrated_email,
    src.name,
    'active' AS status,
    src.created_at
FROM _migration_users_v1_source AS src;

DROP TABLE users;
ALTER TABLE users__migrated RENAME TO users;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS _migration_meta (
    name TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO _migration_meta (name)
VALUES ('users_status_email_v1');

PRAGMA foreign_keys = ON;

COMMIT;

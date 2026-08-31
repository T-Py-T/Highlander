BEGIN IMMEDIATE;

PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS users__rollback;

CREATE TABLE users__rollback (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users__rollback (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

DROP TABLE users;
ALTER TABLE users__rollback RENAME TO users;

DROP INDEX IF EXISTS idx_users_email;
DROP TABLE IF EXISTS _migration_meta;
DROP TABLE IF EXISTS _migration_users_v1_source;

PRAGMA foreign_keys = ON;

COMMIT;

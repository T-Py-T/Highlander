PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

DROP TRIGGER IF EXISTS users_email_not_blank_insert;
DROP TRIGGER IF EXISTS users_email_not_blank_update;
DROP INDEX IF EXISTS users_email_unique_idx;

ALTER TABLE users RENAME TO users__rollback_source;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users__rollback_backup;

DROP TABLE users__rollback_source;

COMMIT;
PRAGMA foreign_keys = ON;

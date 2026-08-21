PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

DROP TRIGGER IF EXISTS users_email_required_insert;
DROP TRIGGER IF EXISTS users_email_required_update;
DROP TRIGGER IF EXISTS users_status_shadow_insert;
DROP TRIGGER IF EXISTS users_status_shadow_update;
DROP TRIGGER IF EXISTS users_status_shadow_delete;
DROP INDEX IF EXISTS users_email_unique;
DROP TABLE IF EXISTS users__rollback_old;

CREATE TABLE users__rollback_old (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users__rollback_old (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

DROP TABLE users;
ALTER TABLE users__rollback_old RENAME TO users;
DROP TABLE IF EXISTS users__status_shadow;

COMMIT;
PRAGMA foreign_keys = ON;

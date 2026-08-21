-- Restore the pre-migration users schema shape after migration.
-- This removes users.status and keeps the current migrated user ids, emails,
-- names, and historical created_at values intact.

PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE TRANSACTION;

DROP TABLE IF EXISTS users__rollback_old_shape;

CREATE TABLE users__rollback_old_shape (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users__rollback_old_shape (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

DROP TABLE users;
ALTER TABLE users__rollback_old_shape RENAME TO users;

COMMIT;

PRAGMA foreign_keys = ON;

-- Should return no rows after rollback.
PRAGMA foreign_key_check;

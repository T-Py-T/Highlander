-- Restore the pre-migration users schema shape (id, email, name, created_at).
-- This is executable after migration.sql. Cleaned email values are retained;
-- rollback restores the old shape, not the pre-cleanup dirty values.
PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

DROP TABLE IF EXISTS users__rollback_new;
CREATE TABLE users__rollback_new (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users__rollback_new (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

DROP TABLE users;
ALTER TABLE users__rollback_new RENAME TO users;

COMMIT;
PRAGMA foreign_keys = ON;

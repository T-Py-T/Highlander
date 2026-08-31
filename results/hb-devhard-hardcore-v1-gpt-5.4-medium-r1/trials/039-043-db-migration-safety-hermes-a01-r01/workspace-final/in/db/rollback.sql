PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

-- Restore the pre-migration users table shape while preserving rows and order links.
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

COMMIT;
PRAGMA foreign_keys = ON;
PRAGMA foreign_key_check;

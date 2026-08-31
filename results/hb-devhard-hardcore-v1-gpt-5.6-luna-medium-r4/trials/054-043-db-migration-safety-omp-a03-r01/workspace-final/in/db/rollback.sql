-- Restore the pre-migration users shape. Cleaned email values remain because the
-- migration does not retain a history table; row and order data are preserved.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

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

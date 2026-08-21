PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS users__rollback_old;
ALTER TABLE users RENAME TO users__rollback_old;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users__rollback_old
ORDER BY created_at, id;

DROP TABLE users__rollback_old;

COMMIT;

PRAGMA foreign_keys = ON;
PRAGMA foreign_key_check;
PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS users__rollback_new;

CREATE TABLE users__rollback_new (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users__rollback_new (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users
ORDER BY created_at, id;

DROP TABLE users;
ALTER TABLE users__rollback_new RENAME TO users;

COMMIT;

PRAGMA foreign_keys = ON;
PRAGMA foreign_key_check;

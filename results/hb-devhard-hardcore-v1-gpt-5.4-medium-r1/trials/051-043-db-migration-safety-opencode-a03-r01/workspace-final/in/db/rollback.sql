PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

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

PRAGMA foreign_key_check;

COMMIT;

PRAGMA foreign_keys = ON;

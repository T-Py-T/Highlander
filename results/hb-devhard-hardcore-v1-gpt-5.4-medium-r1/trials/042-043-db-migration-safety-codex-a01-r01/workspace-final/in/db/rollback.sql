PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

DROP TABLE IF EXISTS users__rollback_old;
DROP TABLE IF EXISTS orders__rollback_old;

CREATE TABLE users__rollback_old (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users__rollback_old (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

CREATE TABLE orders__rollback_old (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders__rollback_old (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders;

DROP TABLE orders;
DROP TABLE users;

ALTER TABLE users__rollback_old RENAME TO users;
ALTER TABLE orders__rollback_old RENAME TO orders;

COMMIT;

PRAGMA foreign_keys = ON;

PRAGMA foreign_key_check;

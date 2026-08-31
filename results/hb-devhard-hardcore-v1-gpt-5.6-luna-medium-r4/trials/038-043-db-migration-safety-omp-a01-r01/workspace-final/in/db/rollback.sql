-- Restore the pre-migration users shape while retaining migrated values and rows.
PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

-- Rename first so SQLite updates the dependent FK before rebuilding users.
ALTER TABLE users RENAME TO users_after_migration;

CREATE TABLE users_old_shape (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users_old_shape (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users_after_migration;

CREATE TABLE orders_old_shape (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users_old_shape(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders_old_shape (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders;

DROP TABLE orders;
ALTER TABLE orders_old_shape RENAME TO orders;
DROP TABLE users_after_migration;
ALTER TABLE users_old_shape RENAME TO users;

COMMIT;

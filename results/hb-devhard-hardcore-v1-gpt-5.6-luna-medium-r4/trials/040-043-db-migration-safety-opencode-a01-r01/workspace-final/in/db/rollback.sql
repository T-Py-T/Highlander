PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

-- Rebuild the dependent table first so users can be replaced safely.
CREATE TABLE orders_rollback (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
INSERT INTO orders_rollback (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at FROM orders;
DROP TABLE orders;

CREATE TABLE users_rollback (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
INSERT INTO users_rollback (id, email, name, created_at)
SELECT id, email, name, created_at FROM users;
DROP TABLE users;
ALTER TABLE users_rollback RENAME TO users;
ALTER TABLE orders_rollback RENAME TO orders;

COMMIT;

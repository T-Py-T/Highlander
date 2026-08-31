-- Restore the pre-migration users schema shape. Cleaned email values remain;
-- original NULL/blank/duplicate values cannot be recovered from the migrated DB.
PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

ALTER TABLE users RENAME TO users__rollback_old;
ALTER TABLE orders RENAME TO orders__rollback_old;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users__rollback_old;

CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders__rollback_old;

DROP TABLE orders__rollback_old;
DROP TABLE users__rollback_old;

COMMIT;

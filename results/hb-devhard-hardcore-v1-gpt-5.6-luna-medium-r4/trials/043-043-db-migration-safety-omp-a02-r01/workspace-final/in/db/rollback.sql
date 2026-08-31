PRAGMA foreign_keys = ON;

-- Roll back the schema shape only. Deterministic email cleanup values remain;
-- original NULL/blank/duplicate values cannot be reconstructed from this schema.
BEGIN TRANSACTION;

ALTER TABLE orders RENAME TO orders_before_rollback;
ALTER TABLE users RENAME TO users_before_rollback;

CREATE TABLE users_old (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users_old (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users_before_rollback;

CREATE TABLE orders_old (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users_old(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders_old (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders_before_rollback;

DROP TABLE orders_before_rollback;
DROP TABLE users_before_rollback;
ALTER TABLE users_old RENAME TO users;
ALTER TABLE orders_old RENAME TO orders;

COMMIT;
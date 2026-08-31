-- Transactional, rerunnable rebuild of users and orders.
-- Dirty-data cleanup: retain the first ada@example.com row (u1), and assign
-- deterministic unique values to u4, u5, and u6 before adding constraints.
PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

-- Move both sides so the dependent rows are copied before either old table is removed.
ALTER TABLE users RENAME TO users__migration_old;
ALTER TABLE orders RENAME TO orders__migration_old;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users (id, email, name, status, created_at)
SELECT
    id,
    CASE id
        WHEN 'u4' THEN 'ada+u4@example.com'
        WHEN 'u5' THEN 'missing+u5@example.invalid'
        WHEN 'u6' THEN 'missing+u6@example.invalid'
        ELSE email
    END,
    name,
    'active',
    created_at
FROM users__migration_old;

CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders__migration_old;

DROP TABLE orders__migration_old;
DROP TABLE users__migration_old;

COMMIT;

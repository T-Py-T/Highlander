-- Safe, repeatable SQLite migration.
-- Dirty data cleanup: keep u1's ada@example.com; map u4 to
-- ada+u4@example.com, u5 to missing+u5@example.invalid, and u6 to
-- missing+u6@example.invalid before adding NOT NULL/UNIQUE email constraints.
-- Rebuilding dependents first keeps every orders.user_id unchanged.

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS orders_new;
DROP TABLE IF EXISTS users_new;

CREATE TABLE users_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users_new (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN 'missing+u6@example.invalid'
        ELSE email
    END,
    name,
    'active',
    created_at
FROM users;

CREATE TABLE orders_new (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users_new(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders_new (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders;

-- Remove the old parent only after its dependent rows have been copied.
DROP TABLE orders;
DROP TABLE users;
ALTER TABLE users_new RENAME TO users;
ALTER TABLE orders_new RENAME TO orders;

COMMIT;

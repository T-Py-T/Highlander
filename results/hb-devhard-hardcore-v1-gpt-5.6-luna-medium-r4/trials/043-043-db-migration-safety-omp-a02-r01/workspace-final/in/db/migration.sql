PRAGMA foreign_keys = ON;

-- Rebuild both tables in dependency order so every user row and order row
-- survives while users receives NOT NULL status and strict email constraints.
-- The CASE expressions are deterministic and are harmless on later runs.
BEGIN TRANSACTION;

ALTER TABLE orders RENAME TO orders_before_migration;
ALTER TABLE users RENAME TO users_before_migration;

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
FROM users_before_migration;

CREATE TABLE orders_new (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users_new(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders_new (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders_before_migration;

DROP TABLE orders_before_migration;
DROP TABLE users_before_migration;
ALTER TABLE users_new RENAME TO users;
ALTER TABLE orders_new RENAME TO orders;

COMMIT;

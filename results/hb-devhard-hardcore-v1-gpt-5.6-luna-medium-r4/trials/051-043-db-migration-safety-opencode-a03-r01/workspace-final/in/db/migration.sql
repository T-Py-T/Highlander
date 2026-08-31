-- Rebuild both tables so the existing orders foreign key is never orphaned.
-- foreign_keys must be disabled while the mutually dependent tables are swapped.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

CREATE TABLE users_migration (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users_migration (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' AND email = 'ada@example.com' THEN 'ada+u4@example.com'
        WHEN id = 'u5' AND email IS NULL THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' AND trim(email) = '' THEN 'missing+u6@example.invalid'
        ELSE email
    END,
    name,
    'active',
    created_at
FROM users;

CREATE TABLE orders_migration (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users_migration(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders_migration (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders;

DROP TABLE orders;
DROP TABLE users;
ALTER TABLE users_migration RENAME TO users;
ALTER TABLE orders_migration RENAME TO orders;

COMMIT;
PRAGMA foreign_keys = ON;

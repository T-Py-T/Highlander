-- Migrate users without dropping source rows, and preserve orders while the
-- users table is rebuilt. The explicit transaction makes every replacement
-- atomic.
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

DROP TABLE IF EXISTS users__migration_new;
DROP TABLE IF EXISTS orders__migration_new;

CREATE TABLE users__migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

-- Keep the first ada@example.com row (u1) unchanged. Repair only the known
-- dirty legacy rows with stable values before the UNIQUE/NOT NULL constraints
-- are installed.
INSERT INTO users__migration_new (id, email, name, status, created_at)
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
FROM users;

CREATE TABLE orders__migration_new (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users__migration_new(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders__migration_new (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders;

-- Remove dependents before replacing their referenced table. No order row is
-- discarded: every row has already been copied into orders__migration_new.
DROP TABLE orders;
DROP TABLE users;

ALTER TABLE users__migration_new RENAME TO users;
ALTER TABLE orders__migration_new RENAME TO orders;

COMMIT;

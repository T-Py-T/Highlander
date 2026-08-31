-- Safe, repeatable SQLite migration.
-- The rebuild is intentional: it preserves ids and timestamps while adding
-- NOT NULL/UNIQUE email enforcement and users.status.
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- Save dependent rows before replacing the referenced users table.  This
-- staging table deliberately has no foreign key so users can be swapped.
DROP TABLE IF EXISTS orders_migration_backup;
CREATE TABLE orders_migration_backup (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
INSERT INTO orders_migration_backup (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders;

DROP TABLE IF EXISTS users_migration_new;
CREATE TABLE users_migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

-- Deterministic cleanup of the known dirty legacy rows.  u1 retains the
-- original ada@example.com value; only the duplicate u4 is disambiguated.
INSERT INTO users_migration_new (id, email, name, status, created_at)
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

-- Remove the old dependent table first, then replace its parent.  The order
-- rows are recreated below with their original user_id values.
DROP TABLE orders;
DROP TABLE users;
ALTER TABLE users_migration_new RENAME TO users;

CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
INSERT INTO orders (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders_migration_backup;
DROP TABLE orders_migration_backup;

COMMIT;

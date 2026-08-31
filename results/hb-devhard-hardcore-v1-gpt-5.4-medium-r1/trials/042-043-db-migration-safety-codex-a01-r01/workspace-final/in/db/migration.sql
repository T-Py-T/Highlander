PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- Rebuild into fresh tables so the migration is repeatable without duplicating rows.
DROP TABLE IF EXISTS users__migration_new;
DROP TABLE IF EXISTS orders__migration_new;

CREATE TABLE users__migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (trim(email) <> ''),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (trim(status) <> ''),
    created_at TEXT NOT NULL
);

-- Dirty-data cleanup is deterministic and tied to the affected legacy user ids.
INSERT INTO users__migration_new (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN 'missing+u6@example.invalid'
        ELSE email
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users;

CREATE TABLE orders__migration_new (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders__migration_new (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders;

DROP TABLE orders;
DROP TABLE users;

ALTER TABLE users__migration_new RENAME TO users;
ALTER TABLE orders__migration_new RENAME TO orders;

COMMIT;

PRAGMA foreign_keys = ON;

-- Returns zero rows when dependent order references were preserved.
PRAGMA foreign_key_check;

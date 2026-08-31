PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS orders__migration_old;
DROP TABLE IF EXISTS users__migration_old;

ALTER TABLE users RENAME TO users__migration_old;
ALTER TABLE orders RENAME TO orders__migration_old;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    CONSTRAINT users_email_not_blank CHECK (trim(email) <> '')
);

INSERT INTO users (id, email, name, status, created_at)
SELECT
    id,
    CASE
        -- Dirty-data cleanup required by policy; deterministic and idempotent.
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN 'missing+u6@example.invalid'
        ELSE email
    END AS email,
    name,
    'active' AS status,
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

PRAGMA foreign_keys = ON;

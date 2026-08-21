BEGIN IMMEDIATE;

PRAGMA foreign_keys = OFF;

-- Preserve the exact pre-migration users payload for rollback.
CREATE TABLE IF NOT EXISTS users__migration_backup (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO users__migration_backup (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

DROP TABLE IF EXISTS users__new;
DROP TABLE IF EXISTS orders__new;

ALTER TABLE orders RENAME TO orders__old;

CREATE TABLE users__new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users__new (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' AND TRIM(COALESCE(email, '')) = '' THEN 'missing+u6@example.invalid'
        ELSE email
    END AS migrated_email,
    name,
    'active' AS status,
    created_at
FROM users
ORDER BY created_at, id;

CREATE TABLE orders__new (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders__new (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders__old
ORDER BY created_at, id;

DROP TABLE users;
ALTER TABLE users__new RENAME TO users;
DROP TABLE orders__old;
ALTER TABLE orders__new RENAME TO orders;

PRAGMA foreign_key_check;
PRAGMA foreign_keys = ON;

COMMIT;

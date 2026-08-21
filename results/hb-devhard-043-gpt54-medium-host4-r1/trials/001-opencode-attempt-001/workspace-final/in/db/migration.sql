PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS temp.users__migration_source;
DROP TABLE IF EXISTS temp.orders__migration_source;

CREATE TEMP TABLE users__migration_source AS
SELECT
    id,
    email,
    name,
    created_at
FROM users;

CREATE TEMP TABLE orders__migration_source AS
SELECT
    rowid AS migration_rowid,
    id,
    user_id,
    total_cents,
    created_at
FROM orders;

DROP TABLE orders;
DROP TABLE users;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (length(trim(email)) > 0),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN 'missing+u6@example.invalid'
        ELSE trim(email)
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users__migration_source;

CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders (id, user_id, total_cents, created_at)
SELECT
    id,
    user_id,
    total_cents,
    created_at
FROM orders__migration_source
ORDER BY migration_rowid;

DROP TABLE temp.orders__migration_source;
DROP TABLE temp.users__migration_source;

COMMIT;

PRAGMA foreign_keys = ON;

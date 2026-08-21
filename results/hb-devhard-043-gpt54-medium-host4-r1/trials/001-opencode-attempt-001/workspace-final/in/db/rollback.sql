PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS temp.users__rollback_source;
DROP TABLE IF EXISTS temp.orders__rollback_source;

CREATE TEMP TABLE users__rollback_source AS
SELECT
    id,
    email,
    name,
    created_at
FROM users;

CREATE TEMP TABLE orders__rollback_source AS
SELECT
    rowid AS rollback_rowid,
    id,
    user_id,
    total_cents,
    created_at
FROM orders;

DROP TABLE orders;
DROP TABLE users;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users (id, email, name, created_at)
SELECT
    id,
    email,
    name,
    created_at
FROM users__rollback_source;

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
FROM orders__rollback_source
ORDER BY rollback_rowid;

DROP TABLE temp.orders__rollback_source;
DROP TABLE temp.users__rollback_source;

COMMIT;

PRAGMA foreign_keys = ON;

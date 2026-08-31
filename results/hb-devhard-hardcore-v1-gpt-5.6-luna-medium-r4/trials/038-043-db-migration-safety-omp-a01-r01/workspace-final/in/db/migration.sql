-- Transactional rebuild: normalize legacy emails before adding NOT NULL/UNIQUE.
-- u4 duplicates the retained u1 address; u5/u6 receive deterministic sentinels.
PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

UPDATE users
SET email = CASE id
    WHEN 'u4' THEN 'ada+u4@example.com'
    WHEN 'u5' THEN 'missing+u5@example.invalid'
    WHEN 'u6' THEN 'missing+u6@example.invalid'
    ELSE email
END
WHERE id IN ('u4', 'u5', 'u6');

-- Rename first so SQLite's dependent FK is updated, then rebuild both tables.
ALTER TABLE users RENAME TO users_before_status_migration;

CREATE TABLE users_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users_new (id, email, name, status, created_at)
SELECT id, email, name, 'active', created_at
FROM users_before_status_migration;

CREATE TABLE orders_new (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users_new(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders_new (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders;

DROP TABLE orders;
ALTER TABLE orders_new RENAME TO orders;
DROP TABLE users_before_status_migration;
ALTER TABLE users_new RENAME TO users;

COMMIT;

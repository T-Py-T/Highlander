-- Restore the pre-migration users column shape while retaining migrated data
-- and every dependent order. This rollback does not restore the old dirty
-- email values; those values are intentionally not recoverable from the
-- migrated schema.
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

DROP TABLE IF EXISTS users__rollback_new;
DROP TABLE IF EXISTS orders__rollback_new;

CREATE TABLE users__rollback_new (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users__rollback_new (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

CREATE TABLE orders__rollback_new (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users__rollback_new(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders__rollback_new (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders;

DROP TABLE orders;
DROP TABLE users;

ALTER TABLE users__rollback_new RENAME TO users;
ALTER TABLE orders__rollback_new RENAME TO orders;

COMMIT;

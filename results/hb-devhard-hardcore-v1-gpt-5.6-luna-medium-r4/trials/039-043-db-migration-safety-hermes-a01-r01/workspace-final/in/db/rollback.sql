-- Restore the pre-migration users schema shape.  This preserves the users,
-- orders, ids, references, names, and current created_at/email values.  The
-- original dirty email values cannot be reconstructed from the migrated
-- schema, so rollback is structural/data-preserving but not byte-for-byte.
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

DROP TABLE IF EXISTS orders_rollback_backup;
CREATE TABLE orders_rollback_backup (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
INSERT INTO orders_rollback_backup (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders;

DROP TABLE IF EXISTS users_rollback_new;
CREATE TABLE users_rollback_new (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
INSERT INTO users_rollback_new (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

DROP TABLE orders;
DROP TABLE users;
ALTER TABLE users_rollback_new RENAME TO users;

CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
INSERT INTO orders (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM orders_rollback_backup;
DROP TABLE orders_rollback_backup;

COMMIT;

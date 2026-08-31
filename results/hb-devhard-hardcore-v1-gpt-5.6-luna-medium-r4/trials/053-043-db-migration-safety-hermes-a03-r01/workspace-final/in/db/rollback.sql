-- Restore the pre-migration users schema shape while retaining every row.
-- Dirty email values remain deterministic cleaned values; the original NULL /
-- blank / duplicate values cannot be reconstructed from the migrated schema.
PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

ALTER TABLE orders RENAME TO __orders_before_users_status_email_rollback;
ALTER TABLE users RENAME TO __users_before_users_status_email_rollback;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users (id, email, name, created_at)
SELECT id, email, name, created_at
FROM __users_before_users_status_email_rollback;

CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM __orders_before_users_status_email_rollback;

DROP TABLE __orders_before_users_status_email_rollback;
DROP TABLE __users_before_users_status_email_rollback;
DROP TABLE IF EXISTS __migration_metadata;

COMMIT;

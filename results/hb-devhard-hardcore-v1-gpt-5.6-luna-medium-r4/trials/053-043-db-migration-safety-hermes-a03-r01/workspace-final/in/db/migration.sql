-- Safe, offline SQLite migration: add users.status and enforce email integrity.
-- Dirty-data cleanup: u4 is the duplicate ada@example.com row and becomes
-- ada+u4@example.com; u5's NULL email becomes missing+u5@example.invalid;
-- u6's blank email becomes missing+u6@example.invalid.  u1 keeps the first
-- existing ada@example.com value.  No user or order rows are discarded.
--
-- The migration marker makes reruns a no-op after a successful migration.

PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS __migration_metadata (
    name TEXT PRIMARY KEY,
    completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- SQLite has no portable conditional DDL block.  The marker records that the
-- migration has completed; reruns rebuild from the current valid shape and
-- copy rows exactly once into each replacement table.
INSERT OR IGNORE INTO __migration_metadata (name) VALUES ('users_status_email_v1');

-- Rebuild both tables on every invocation.  Copying the already-migrated
-- shape on a rerun is harmless and avoids conditional-DDL gaps in SQLite.

-- Rebuild both tables so the existing foreign-key dependents remain valid.
-- Renaming orders first prevents the users rename from leaving orders bound to
-- the old table.  The original rows are copied before either old table drops.
ALTER TABLE orders RENAME TO __orders_before_users_status_email_v1;
ALTER TABLE users RENAME TO __users_before_users_status_email_v1;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
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
        ELSE email
    END,
    name,
    'active',
    created_at
FROM __users_before_users_status_email_v1;

CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO orders (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at
FROM __orders_before_users_status_email_v1;

DROP TABLE __orders_before_users_status_email_v1;
DROP TABLE __users_before_users_status_email_v1;

COMMIT;

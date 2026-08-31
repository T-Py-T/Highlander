-- Rebuild users without dropping dependent order data. The foreign-key pragma
-- must be set before the transaction; it is a no-op once BEGIN has started.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

-- Normalize the known legacy values before copying. These updates are
-- deterministic and therefore harmless on a repeated run.
UPDATE users
SET email = 'ada+u4@example.com'
WHERE id = 'u4' AND email = 'ada@example.com';
UPDATE users
SET email = 'missing+u5@example.invalid'
WHERE id = 'u5' AND email IS NULL;
UPDATE users
SET email = 'missing+u6@example.invalid'
WHERE id = 'u6' AND (email IS NULL OR trim(email) = '');

CREATE TABLE users__migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

-- A rerun rebuilds the same canonical shape; all migrated rows use the
-- required default status.
INSERT INTO users__migration_new (id, email, name, status, created_at)
SELECT id, email, name, 'active', created_at
FROM users;

DROP TABLE users;
ALTER TABLE users__migration_new RENAME TO users;

COMMIT;
PRAGMA foreign_keys = ON;

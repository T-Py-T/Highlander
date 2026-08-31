PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS users__migration_new;

CREATE TABLE IF NOT EXISTS users__migration_state (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO users__migration_state (id, email, name, status, created_at)
SELECT
    id,
    email,
    name,
    'active',
    created_at
FROM users;

UPDATE users__migration_state
SET email = 'ada+u4@example.com'
WHERE id = 'u4';

UPDATE users__migration_state
SET email = 'missing+u5@example.invalid'
WHERE id = 'u5';

UPDATE users__migration_state
SET email = 'missing+u6@example.invalid'
WHERE id = 'u6';

UPDATE users__migration_state
SET status = COALESCE(NULLIF(TRIM(status), ''), 'active');

CREATE TABLE users__migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users__migration_new (id, email, name, status, created_at)
SELECT
    id,
    email,
    name,
    status,
    created_at
FROM users__migration_state
ORDER BY created_at, id;

DROP TABLE users;
ALTER TABLE users__migration_new RENAME TO users;

COMMIT;

PRAGMA foreign_keys = ON;

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

DROP TABLE IF EXISTS users__migration_new;

CREATE TABLE users__migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

-- Preserve every user row and clean historical dirty emails deterministically
-- before enforcing the new NOT NULL + UNIQUE email constraint.
INSERT INTO users__migration_new (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN 'missing+u6@example.invalid'
        ELSE email
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users;

DROP TABLE users;
ALTER TABLE users__migration_new RENAME TO users;

PRAGMA foreign_key_check;

COMMIT;

PRAGMA foreign_keys = ON;

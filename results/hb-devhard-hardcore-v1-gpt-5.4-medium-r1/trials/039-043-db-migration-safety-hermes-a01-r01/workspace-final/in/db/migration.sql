PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

-- Rebuild users into the target shape inside the same transaction.
-- Cleanup is deterministic so rerunning the script preserves the same user ids,
-- cleaned email values, created_at history, and dependent order references.
DROP TABLE IF EXISTS users__migration_new;

CREATE TABLE users__migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (trim(email) <> ''),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users__migration_new (id, email, name, status, created_at)
SELECT
    id,
    CASE
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN 'missing+u6@example.invalid'
        WHEN email IS NULL OR trim(email) = '' THEN 'missing+' || id || '@example.invalid'
        WHEN email = 'ada@example.com' AND id <> 'u1' THEN 'ada+' || id || '@example.com'
        ELSE trim(email)
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users;

DROP TABLE users;
ALTER TABLE users__migration_new RENAME TO users;

COMMIT;
PRAGMA foreign_keys = ON;
PRAGMA foreign_key_check;

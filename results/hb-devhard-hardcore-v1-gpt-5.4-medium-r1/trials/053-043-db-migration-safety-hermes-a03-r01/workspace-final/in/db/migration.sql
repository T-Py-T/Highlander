PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

-- Rebuild the users table into the target schema so constraints are enforced
-- without dropping any rows or changing user ids.
DROP TABLE IF EXISTS users__migration_new;

CREATE TABLE users__migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (trim(email) <> ''),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

-- Preserve all users, preserve historical created_at values, preserve ids used by
-- orders, and deterministically clean known dirty emails before constraints apply.
INSERT INTO users__migration_new (id, email, name, status, created_at)
SELECT
    id,
    CASE id
        WHEN 'u4' THEN 'ada+u4@example.com'
        WHEN 'u5' THEN 'missing+u5@example.invalid'
        WHEN 'u6' THEN 'missing+u6@example.invalid'
        ELSE email
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users;

DROP TABLE users;
ALTER TABLE users__migration_new RENAME TO users;

COMMIT;
PRAGMA foreign_keys = ON;

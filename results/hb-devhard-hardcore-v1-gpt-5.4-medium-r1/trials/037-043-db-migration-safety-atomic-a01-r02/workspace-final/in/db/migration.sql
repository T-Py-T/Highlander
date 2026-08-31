PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

-- Rebuild users in one transaction so we can add NOT NULL/UNIQUE/CHECK
-- constraints without dropping user or order data.
--
-- Dirty-data cleanup applied during copy:
-- - keep the first ada@example.com row unchanged
-- - rewrite duplicate user u4 to ada+u4@example.com
-- - rewrite null email user u5 to missing+u5@example.invalid
-- - rewrite blank email user u6 to missing+u6@example.invalid
--
-- The rebuild is repeatable: running this script again recreates the same
-- target shape and re-applies the same deterministic email mapping.
DROP TABLE IF EXISTS users__migration_new;
DROP TABLE IF EXISTS users__migration_old;

ALTER TABLE users RENAME TO users__migration_old;

CREATE TABLE users__migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (length(trim(email)) > 0),
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
        ELSE trim(email)
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users__migration_old;

ALTER TABLE users__migration_new RENAME TO users;
DROP TABLE users__migration_old;

COMMIT;

PRAGMA foreign_keys = ON;
PRAGMA foreign_key_check;

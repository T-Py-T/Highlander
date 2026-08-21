PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS users__migration_old;
ALTER TABLE users RENAME TO users__migration_old;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (LENGTH(TRIM(email)) > 0),
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
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users__migration_old
ORDER BY created_at, id;

DROP TABLE users__migration_old;

COMMIT;

PRAGMA foreign_keys = ON;
PRAGMA foreign_key_check;

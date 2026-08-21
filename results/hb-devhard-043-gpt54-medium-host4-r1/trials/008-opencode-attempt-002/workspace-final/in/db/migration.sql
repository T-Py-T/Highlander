PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

CREATE TEMP TABLE IF NOT EXISTS _users_migration_counts (
    user_count INTEGER NOT NULL,
    order_count INTEGER NOT NULL
);

CREATE TEMP TABLE IF NOT EXISTS _users_migration_assert (
    ok INTEGER NOT NULL CHECK (ok = 1)
);

DELETE FROM _users_migration_counts;

INSERT INTO _users_migration_counts (user_count, order_count)
SELECT
    (SELECT COUNT(*) FROM users),
    (SELECT COUNT(*) FROM orders);

DELETE FROM _users_migration_assert;

DROP TABLE IF EXISTS users__migration_new;

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
    CASE
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN 'missing+u6@example.invalid'
        WHEN email IS NULL OR TRIM(email) = '' THEN 'missing+' || id || '@example.invalid'
        ELSE email
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users;

INSERT INTO _users_migration_assert (ok)
SELECT CASE
    WHEN (SELECT COUNT(*) FROM users__migration_new) = (SELECT user_count FROM _users_migration_counts)
        THEN 1
    ELSE 0
END;

DROP TABLE users;
ALTER TABLE users__migration_new RENAME TO users;

DELETE FROM _users_migration_assert;

INSERT INTO _users_migration_assert (ok)
SELECT CASE
    WHEN (SELECT COUNT(*) FROM users) = (SELECT user_count FROM _users_migration_counts)
        THEN 1
    ELSE 0
END;

DELETE FROM _users_migration_assert;

INSERT INTO _users_migration_assert (ok)
SELECT CASE
    WHEN (SELECT COUNT(*) FROM orders) = (SELECT order_count FROM _users_migration_counts)
        THEN 1
    ELSE 0
END;

DELETE FROM _users_migration_assert;

INSERT INTO _users_migration_assert (ok)
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pragma_foreign_key_check)
        THEN 0
    ELSE 1
END;

COMMIT;

PRAGMA foreign_keys = ON;

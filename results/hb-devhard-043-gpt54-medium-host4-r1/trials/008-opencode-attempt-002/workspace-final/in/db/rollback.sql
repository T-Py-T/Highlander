PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

CREATE TEMP TABLE IF NOT EXISTS _users_rollback_assert (
    ok INTEGER NOT NULL CHECK (ok = 1)
);

DROP TABLE IF EXISTS users__rollback_new;

CREATE TABLE users__rollback_new (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users__rollback_new (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

DROP TABLE users;
ALTER TABLE users__rollback_new RENAME TO users;

DELETE FROM _users_rollback_assert;

INSERT INTO _users_rollback_assert (ok)
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pragma_foreign_key_check)
        THEN 0
    ELSE 1
END;

COMMIT;

PRAGMA foreign_keys = ON;

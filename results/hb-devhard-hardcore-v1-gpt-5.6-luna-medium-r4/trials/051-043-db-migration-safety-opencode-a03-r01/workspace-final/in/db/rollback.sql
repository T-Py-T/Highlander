-- Roll back the schema shape only. Cleanup addresses remain because the
-- original duplicate/NULL/blank values cannot be inferred safely.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

CREATE TABLE users_rollback (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users_rollback (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

DROP TABLE users;
ALTER TABLE users_rollback RENAME TO users;

COMMIT;
PRAGMA foreign_keys = ON;

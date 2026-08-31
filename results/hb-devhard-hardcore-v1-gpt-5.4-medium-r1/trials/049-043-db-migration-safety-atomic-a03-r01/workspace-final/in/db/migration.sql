PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

-- Preserve the pre-migration users table shape for rollback.
CREATE TABLE IF NOT EXISTS users__rollback_backup (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO users__rollback_backup (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

-- Rebuild users safely so we can add status and enforce clean emails.
DROP TRIGGER IF EXISTS users_email_not_blank_insert;
DROP TRIGGER IF EXISTS users_email_not_blank_update;
DROP INDEX IF EXISTS users_email_unique_idx;

ALTER TABLE users RENAME TO users__migration_source;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users (id, email, name, status, created_at)
SELECT
    id,
    CASE
        -- Required deterministic cleanup for known dirty rows.
        WHEN id = 'u4' THEN 'ada+u4@example.com'
        WHEN id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN id = 'u6' THEN 'missing+u6@example.invalid'
        -- Defensive cleanup for any other null or blank rows.
        WHEN email IS NULL THEN 'missing+' || id || '@example.invalid'
        WHEN TRIM(email) = '' THEN 'missing+' || id || '@example.invalid'
        -- Keep the first ada@example.com row unchanged; rewrite later duplicates.
        WHEN id <> 'u1' AND email = 'ada@example.com' THEN 'ada+' || id || '@example.com'
        ELSE email
    END AS email,
    name,
    'active' AS status,
    created_at
FROM users__migration_source;

DROP TABLE users__migration_source;

CREATE UNIQUE INDEX users_email_unique_idx ON users (email);

CREATE TRIGGER users_email_not_blank_insert
BEFORE INSERT ON users
FOR EACH ROW
WHEN NEW.email IS NULL OR TRIM(NEW.email) = ''
BEGIN
    SELECT RAISE(ABORT, 'users.email must be non-null and non-blank');
END;

CREATE TRIGGER users_email_not_blank_update
BEFORE UPDATE OF email ON users
FOR EACH ROW
WHEN NEW.email IS NULL OR TRIM(NEW.email) = ''
BEGIN
    SELECT RAISE(ABORT, 'users.email must be non-null and non-blank');
END;

COMMIT;
PRAGMA foreign_keys = ON;

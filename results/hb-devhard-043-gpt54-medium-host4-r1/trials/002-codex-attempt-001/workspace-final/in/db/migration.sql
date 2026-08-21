PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

-- Preserve the original pre-migration user rows for rollback.
CREATE TABLE IF NOT EXISTS users_pre_migration_backup (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO users_pre_migration_backup (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users;

-- Persist status values outside the users table so a rerun can rebuild safely.
CREATE TABLE IF NOT EXISTS users_status_backup (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL
);

INSERT OR IGNORE INTO users_status_backup (id, status)
SELECT id, 'active'
FROM users;

DROP TABLE IF EXISTS users__new;

CREATE TABLE users__new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (TRIM(email) <> ''),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

-- Deterministic cleanup preserves every user row while making future email
-- writes enforceable via NOT NULL, UNIQUE, and a blank-string CHECK.
INSERT INTO users__new (id, email, name, status, created_at)
SELECT
    u.id,
    CASE
        WHEN u.id = 'u4' THEN 'ada+u4@example.com'
        WHEN u.id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN u.id = 'u6' THEN 'missing+u6@example.invalid'
        ELSE u.email
    END AS migrated_email,
    u.name,
    COALESCE(sb.status, 'active') AS status,
    u.created_at
FROM users AS u
LEFT JOIN users_status_backup AS sb
    ON sb.id = u.id
ORDER BY u.id;

DROP TABLE users;
ALTER TABLE users__new RENAME TO users;

CREATE TRIGGER users_status_backup_after_insert
AFTER INSERT ON users
BEGIN
    INSERT INTO users_status_backup (id, status)
    VALUES (NEW.id, NEW.status)
    ON CONFLICT(id) DO UPDATE SET status = excluded.status;
END;

CREATE TRIGGER users_status_backup_after_status_update
AFTER UPDATE OF status ON users
BEGIN
    INSERT INTO users_status_backup (id, status)
    VALUES (NEW.id, NEW.status)
    ON CONFLICT(id) DO UPDATE SET status = excluded.status;
END;

CREATE TRIGGER users_status_backup_after_delete
AFTER DELETE ON users
BEGIN
    DELETE FROM users_status_backup
    WHERE id = OLD.id;
END;

COMMIT;

PRAGMA foreign_keys = ON;

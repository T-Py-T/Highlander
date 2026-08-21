PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

-- Persist status values across reruns. The first migration seeds every user as active.
CREATE TABLE IF NOT EXISTS users__status_shadow (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL
);

INSERT OR IGNORE INTO users__status_shadow (id, status)
SELECT id, 'active'
FROM users;

DELETE FROM users__status_shadow
WHERE id NOT IN (SELECT id FROM users);

DROP TABLE IF EXISTS users__migration_new;

CREATE TABLE users__migration_new (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

-- Deterministic cleanup for legacy dirty emails.
INSERT INTO users__migration_new (id, email, name, status, created_at)
SELECT
    u.id,
    CASE u.id
        WHEN 'u4' THEN 'ada+u4@example.com'
        WHEN 'u5' THEN 'missing+u5@example.invalid'
        WHEN 'u6' THEN 'missing+u6@example.invalid'
        ELSE u.email
    END AS email,
    u.name,
    COALESCE(s.status, 'active') AS status,
    u.created_at
FROM users AS u
LEFT JOIN users__status_shadow AS s
    ON s.id = u.id;

DROP TABLE users;
ALTER TABLE users__migration_new RENAME TO users;

CREATE UNIQUE INDEX users_email_unique
    ON users(email);

CREATE TRIGGER users_email_required_insert
BEFORE INSERT ON users
FOR EACH ROW
WHEN NEW.email IS NULL OR TRIM(NEW.email) = ''
BEGIN
    SELECT RAISE(ABORT, 'users.email must be non-null and non-blank');
END;

CREATE TRIGGER users_email_required_update
BEFORE UPDATE OF email ON users
FOR EACH ROW
WHEN NEW.email IS NULL OR TRIM(NEW.email) = ''
BEGIN
    SELECT RAISE(ABORT, 'users.email must be non-null and non-blank');
END;

CREATE TRIGGER users_status_shadow_insert
AFTER INSERT ON users
FOR EACH ROW
BEGIN
    INSERT INTO users__status_shadow (id, status)
    VALUES (NEW.id, NEW.status)
    ON CONFLICT(id) DO UPDATE SET status = excluded.status;
END;

CREATE TRIGGER users_status_shadow_update
AFTER UPDATE OF id, status ON users
FOR EACH ROW
BEGIN
    DELETE FROM users__status_shadow
    WHERE id = OLD.id
      AND OLD.id <> NEW.id;

    INSERT INTO users__status_shadow (id, status)
    VALUES (NEW.id, NEW.status)
    ON CONFLICT(id) DO UPDATE SET status = excluded.status;
END;

CREATE TRIGGER users_status_shadow_delete
AFTER DELETE ON users
FOR EACH ROW
BEGIN
    DELETE FROM users__status_shadow
    WHERE id = OLD.id;
END;

COMMIT;
PRAGMA foreign_keys = ON;

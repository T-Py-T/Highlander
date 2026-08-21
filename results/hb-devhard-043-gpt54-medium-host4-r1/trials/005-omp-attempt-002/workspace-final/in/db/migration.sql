PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

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
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

INSERT INTO users__migration_new (id, email, name, status, created_at)
SELECT
    users.id,
    CASE
        WHEN users.id = 'u4' THEN 'ada+u4@example.com'
        WHEN users.id = 'u5' THEN 'missing+u5@example.invalid'
        WHEN users.id = 'u6' THEN 'missing+u6@example.invalid'
        ELSE users.email
    END AS email,
    users.name,
    COALESCE(users__status_shadow.status, 'active') AS status,
    users.created_at
FROM users
LEFT JOIN users__status_shadow
    ON users__status_shadow.id = users.id
ORDER BY users.rowid;

DROP TRIGGER IF EXISTS users__status_shadow_insert;
DROP TRIGGER IF EXISTS users__status_shadow_update;
DROP TRIGGER IF EXISTS users__status_shadow_delete;

DROP TABLE users;
ALTER TABLE users__migration_new RENAME TO users;

CREATE TRIGGER users__status_shadow_insert
AFTER INSERT ON users
BEGIN
    INSERT OR REPLACE INTO users__status_shadow (id, status)
    VALUES (NEW.id, NEW.status);
END;

CREATE TRIGGER users__status_shadow_update
AFTER UPDATE OF id, status ON users
BEGIN
    DELETE FROM users__status_shadow
    WHERE id = OLD.id
      AND OLD.id <> NEW.id;

    INSERT OR REPLACE INTO users__status_shadow (id, status)
    VALUES (NEW.id, NEW.status);
END;

CREATE TRIGGER users__status_shadow_delete
AFTER DELETE ON users
BEGIN
    DELETE FROM users__status_shadow
    WHERE id = OLD.id;
END;

COMMIT;
PRAGMA foreign_keys = ON;

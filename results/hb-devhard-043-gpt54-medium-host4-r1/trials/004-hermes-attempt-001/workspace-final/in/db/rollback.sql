PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS users__rollback;

CREATE TABLE users__rollback (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users__rollback (id, email, name, created_at)
SELECT backup.id, backup.email, backup.name, backup.created_at
FROM _users_pre_migration_backup AS backup
WHERE EXISTS (
    SELECT 1
    FROM sqlite_master
    WHERE type = 'table'
      AND name = '_users_pre_migration_backup'
);

INSERT INTO users__rollback (id, email, name, created_at)
SELECT users.id, users.email, users.name, users.created_at
FROM users
WHERE NOT EXISTS (
    SELECT 1
    FROM sqlite_master
    WHERE type = 'table'
      AND name = '_users_pre_migration_backup'
);

DROP TABLE users;
ALTER TABLE users__rollback RENAME TO users;

PRAGMA foreign_key_check;

COMMIT;

PRAGMA foreign_keys = ON;

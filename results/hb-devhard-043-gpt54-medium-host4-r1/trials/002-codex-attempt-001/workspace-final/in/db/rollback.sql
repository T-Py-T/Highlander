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
SELECT id, email, name, created_at
FROM users_pre_migration_backup
ORDER BY id;

DROP TABLE users;
ALTER TABLE users__rollback RENAME TO users;

DROP TRIGGER IF EXISTS users_status_backup_after_insert;
DROP TRIGGER IF EXISTS users_status_backup_after_status_update;
DROP TRIGGER IF EXISTS users_status_backup_after_delete;
DROP TABLE IF EXISTS users_status_backup;
DROP TABLE IF EXISTS users_pre_migration_backup;

COMMIT;

PRAGMA foreign_keys = ON;

PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE TRANSACTION;

DROP TABLE IF EXISTS users__rollback_source;

CREATE TABLE users__rollback_source AS
SELECT id, email, name, created_at
FROM users;

DROP TABLE users;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO users (id, email, name, created_at)
SELECT id, email, name, created_at
FROM users__rollback_source;

DROP TABLE users__rollback_source;

COMMIT;

PRAGMA foreign_keys = ON;

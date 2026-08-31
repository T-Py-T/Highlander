PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

-- Copy dependents before replacing users so every order and user_id survives.
CREATE TABLE orders_migration (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
INSERT INTO orders_migration (id, user_id, total_cents, created_at)
SELECT id, user_id, total_cents, created_at FROM orders;
DROP TABLE orders;

-- CASE expressions are deterministic and are no-ops after the first run.
CREATE TABLE users_migration (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);
INSERT INTO users_migration (id, email, name, status, created_at)
SELECT id,
       CASE id
           WHEN 'u4' THEN 'ada+u4@example.com'
           WHEN 'u5' THEN 'missing+u5@example.invalid'
           WHEN 'u6' THEN 'missing+u6@example.invalid'
           ELSE email
       END,
       name,
       'active',
       created_at
FROM users;
DROP TABLE users;
ALTER TABLE users_migration RENAME TO users;
ALTER TABLE orders_migration RENAME TO orders;

COMMIT;

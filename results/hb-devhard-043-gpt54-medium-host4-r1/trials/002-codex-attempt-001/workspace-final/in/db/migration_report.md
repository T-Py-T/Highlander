# Migration Report

## Strategy

The migration rebuilds `users` inside `BEGIN IMMEDIATE ... COMMIT` with `PRAGMA foreign_keys = OFF` for the table swap, then re-enables foreign keys afterward. It copies every existing user row into a new `users` table that adds:

- `status TEXT NOT NULL DEFAULT 'active'`
- `email TEXT NOT NULL UNIQUE CHECK (TRIM(email) <> '')`

`orders` is left in place so all existing order rows and `orders.user_id` values continue to point at the same user ids after the table rename.

## Dirty-data cleanup

The cleanup is deterministic and documented in the migration SQL:

- `u4` keeps its row and migrates from duplicate `ada@example.com` to `ada+u4@example.com`
- `u5` keeps its row and migrates from `NULL` to `missing+u5@example.invalid`
- `u6` keeps its row and migrates from blank `''` to `missing+u6@example.invalid`
- `u1`, `u2`, and `u3` keep their existing emails unchanged

Historical `created_at` values are copied forward without modification.

## Idempotency approach

The migration is rerunnable because it:

- keeps a one-time `users_pre_migration_backup` table with the original four-column rows for rollback
- keeps a persistent `users_status_backup` table plus triggers so status values survive later reruns
- rebuilds `users` from current rows using stable user ids and the same deterministic email cleanup rules

Running the migration again does not duplicate users or orders and does not overwrite the original rollback snapshot.

## Rollback behavior

`rollback.sql` rebuilds `users` back to the pre-migration shape:

- `id`
- `email`
- `name`
- `created_at`

It restores those values from `users_pre_migration_backup`, so the original duplicate, `NULL`, and blank legacy emails come back as part of rollback. The rollback script also removes the migration helper tables and triggers.

## Postcheck queries

Run:

```sh
sqlite3 your.db < in/db/postcheck.sql
```

The postcheck script verifies:

- user and order row counts
- preserved dependent orders for `u4`, `u5`, and `u6`
- exact cleaned email values for `u4`, `u5`, and `u6`
- no null or blank emails remain
- email uniqueness
- `status` is present and non-null with default `'active'`
- the `email` column is non-null and backed by a unique constraint
- foreign key integrity via `PRAGMA foreign_key_check`

# Migration report

## Strategy

The migration rebuilds the existing `users` table inside an explicit transaction instead of deleting data and recreating an empty table. This preserves every user row, keeps all `orders.user_id` references unchanged, and leaves historical `created_at` values untouched.

Steps performed by `migration.sql`:

1. Start an explicit transaction with `BEGIN IMMEDIATE`.
2. Temporarily disable foreign-key enforcement while replacing the `users` table shape.
3. Create `users__migration_new` with the target schema:
   - `id TEXT PRIMARY KEY`
   - `email TEXT NOT NULL UNIQUE CHECK (trim(email) <> '')`
   - `name TEXT NOT NULL`
   - `status TEXT NOT NULL DEFAULT 'active'`
   - `created_at TEXT NOT NULL`
4. Copy all existing users into the replacement table while preserving ids and `created_at`, and while applying the deterministic email cleanup.
5. Replace the old `users` table by dropping it and renaming the replacement table to `users`.
6. Re-enable foreign keys and commit.

## Dirty-data cleanup

The migration preserves all existing users and applies the required cleanup values exactly:

- `u4`: `ada@example.com` -> `ada+u4@example.com`
- `u5`: `NULL` -> `missing+u5@example.invalid`
- `u6`: `''` -> `missing+u6@example.invalid`

The first valid `ada@example.com` row (`u1`) is left unchanged.

## Idempotency approach

The migration is safe to run twice because it always rebuilds the `users` table from the current `users` contents into the same target schema and reapplies the same deterministic cleanup values. Running it again does not duplicate users, does not change user ids, and does not duplicate or orphan orders.

## Rollback behavior and limitation

`rollback.sql` restores the pre-migration `users` schema shape to exactly these columns:

- `id`
- `email`
- `name`
- `created_at`

It preserves all user rows and order rows by copying the current `users` data into a replacement table with the old shape and renaming that replacement table back to `users`.

Limitation: the rollback restores the old schema shape, but it does not resurrect the original invalid legacy email values. The cleaned migrated email values remain in place after rollback.

## Postcheck queries to run

Execute `postcheck.sql` after the migration. It verifies:

- user and order row counts
- preserved dependent orders for `u4`, `u5`, and `u6`
- deterministic cleaned email values for the dirty users
- absence of null/blank emails
- absence of duplicate email groups
- absence of null statuses
- presence of the migrated `users` table definition and unique index metadata
- absence of foreign-key violations via `PRAGMA foreign_key_check`

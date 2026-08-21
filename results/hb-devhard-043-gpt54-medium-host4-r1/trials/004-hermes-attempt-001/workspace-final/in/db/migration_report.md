# Migration report

## Strategy

The migration rebuilds `users` inside an explicit `BEGIN IMMEDIATE ... COMMIT` transaction with foreign-key enforcement temporarily disabled for the table swap. It first snapshots the original user rows into `_users_pre_migration_backup`, then recreates `users` with the target schema:

- `id TEXT PRIMARY KEY`
- `email TEXT NOT NULL UNIQUE CHECK (trim(email) <> '')`
- `name TEXT NOT NULL`
- `status TEXT NOT NULL DEFAULT 'active'`
- `created_at TEXT NOT NULL`

Orders are not rewritten. The migration preserves every existing `users.id`, so `orders.user_id` values continue to point at the same user ids after the swap.

## Dirty-data cleanup

The migration preserves all users and applies deterministic cleanup while copying from `_users_pre_migration_backup`:

- `u1` keeps `ada@example.com`.
- Duplicate `u4` becomes `ada+u4@example.com`.
- Null-email `u5` becomes `missing+u5@example.invalid`.
- Blank-email `u6` becomes `missing+u6@example.invalid`.
- Historical `created_at` values are copied through unchanged.

## Idempotency approach

The script is safe to run twice because it always rebuilds `users` from `_users_pre_migration_backup`, not from the already-migrated table. `_users_pre_migration_backup` is created with `IF NOT EXISTS`, and original rows are inserted with `INSERT OR IGNORE`, so rerunning the migration does not duplicate rows or drift the cleaned email values.

## Rollback behavior and limitation

`rollback.sql` restores the old `users` schema shape (`id`, `email`, `name`, `created_at`) in a transaction. When `_users_pre_migration_backup` is present, rollback restores the original pre-migration user data, including the dirty legacy emails. If that backup table has been removed manually, rollback falls back to restoring only the old schema shape from the current `users` data, which preserves rows and order references but cannot reconstruct the original dirty email values.

## Postcheck queries to run

After migration, execute `postcheck.sql`. It verifies:

- user and order row counts
- preservation of dependent orders for `u4`, `u5`, and `u6`
- deterministic cleaned emails for the dirty users
- preserved `created_at` values for dirty users
- no remaining null/blank emails and no duplicate email values
- `email` and `status` constraint metadata on the rebuilt `users` table
- foreign-key integrity via `PRAGMA foreign_key_check`

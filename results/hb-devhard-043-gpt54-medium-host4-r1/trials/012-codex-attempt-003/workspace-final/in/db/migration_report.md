# Migration Report

## Strategy

The migration rebuilds `users` inside an explicit `BEGIN IMMEDIATE TRANSACTION` while `PRAGMA foreign_keys` is temporarily disabled. A persistent `users__migration_backup` table captures the pre-migration `users` rows before any rewrite. The rebuilt table keeps the same `id`, `name`, and `created_at` values, adds `status TEXT NOT NULL DEFAULT 'active'`, and enforces `email TEXT NOT NULL UNIQUE`.

## Dirty-data cleanup

The copy step rewrites only the known dirty rows with deterministic values:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

All other user emails are copied as-is. Because `users.id` values are preserved, dependent orders for `u4`, `u5`, and `u6` continue to reference the same users after the rebuild.

## Idempotency

The migration is stable to rerun on the same migrated database:

- `users__migration_backup` is created with `IF NOT EXISTS`.
- Backup inserts use `INSERT OR IGNORE`, so the original rollback snapshot is retained.
- The migration always rebuilds from the current `users` table, and the cleanup `CASE` expressions only rewrite the original dirty values. Once cleaned, those rows pass through unchanged on later runs.

## Rollback behavior

Run `sqlite3 <db> < in/db/rollback.sql` after the migration to restore the old `users` schema shape: `id`, `email`, `name`, `created_at`. The rollback restores rows from `users__migration_backup`, so the original pre-migration email values return as well. Order rows are preserved because user ids do not change.

Rollback limitation: `rollback.sql` depends on the persistent `users__migration_backup` table created by `migration.sql`. If that backup table is removed, rollback can no longer restore the original email values.

## Post-migration checks

Run `sqlite3 <db> < in/db/postcheck.sql` after the migration. The checks verify:

- user and order row counts
- preserved dependent orders for `u4`, `u5`, and `u6`
- cleaned deterministic email values for dirty users
- absence of null or blank emails
- absence of duplicate email groups
- presence of populated `status` values plus `users` table/index metadata

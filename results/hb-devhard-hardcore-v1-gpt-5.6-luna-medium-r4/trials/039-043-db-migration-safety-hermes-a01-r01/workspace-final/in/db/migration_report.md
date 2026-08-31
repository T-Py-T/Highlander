# Migration report

## Strategy

`migration.sql` runs in an explicit SQLite transaction. It first copies every order into a staging table without a foreign key, creates a replacement `users` table with `email TEXT NOT NULL UNIQUE` and `status TEXT NOT NULL DEFAULT 'active'`, and copies users while retaining `id`, `name`, and historical `created_at`. It then replaces `users` and recreates `orders` with the same order ids and `user_id` values.

Orders are staged before the parent-table replacement and recreated afterward, so dependent rows for `u4`, `u5`, and `u6` remain attached to those same user ids.

## Dirty-data cleanup

The duplicate `u4` email becomes `ada+u4@example.com`; NULL `u5` becomes `missing+u5@example.invalid`; blank `u6` becomes `missing+u6@example.invalid`. The original `ada@example.com` on `u1` and all historical timestamps are retained. `status` is set to `active` for every migrated user.

## Idempotency

The migration uses table replacement rather than one-time ALTER statements. Running it again stages and rewrites the already-clean rows with the same ids, values, and order references; the cleanup CASE is deterministic and does not insert duplicate users. Each run is atomic.

## Rollback behavior and limitation

`rollback.sql` is intended to run after the migration. It rebuilds `users` to the legacy shape (`id`, `email`, `name`, `created_at`) and recreates `orders` while preserving row counts and references. It does not restore the original dirty email bytes: the migration intentionally replaces NULL/blank/duplicate values, and the old values are not retained in the migrated schema. The rollback is therefore structural and row-preserving, not a reversal of those cleanup values.

## Postcheck

Run `postcheck.sql` after migration. It checks:

- user and order row counts;
- preservation of order ids and `user_id` references;
- the three deterministic dirty-user email values;
- non-null/unique email behavior and the `status` NOT NULL/default declaration;
- the users table foreign-key relationship for orders.

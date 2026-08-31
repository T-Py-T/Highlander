# Migration Report

## Strategy

The migration rebuilds `users` inside an explicit `BEGIN IMMEDIATE` transaction with foreign-key enforcement temporarily disabled for the table swap. It copies every existing user row into a new `users__migration_new` table, preserves the original `id`, `name`, and `created_at` values, then drops the old `users` table and renames the rebuilt table into place. Because `orders.user_id` continues to point at the same user ids, dependent orders remain attached to the same users after the rebuild.

## Dirty-data cleanup

The migration normalizes existing dirty emails before the new `NOT NULL UNIQUE` constraint is enforced:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

It also includes a deterministic fallback for any other pre-existing `NULL` or blank email rows: `missing+<id>@example.invalid`.

## Idempotency approach

The script is rerunnable because it always rebuilds `users` from the current contents of `users`, recreates the staging table with `DROP TABLE IF EXISTS users__migration_new`, and rewrites the same deterministic cleaned email values for the known dirty rows. Re-running the migration does not duplicate users or orders and leaves the cleaned emails stable.

## Rollback behavior and limitation

`rollback.sql` restores the pre-migration `users` schema shape to exactly four columns: `id`, `email`, `name`, `created_at`. It preserves the same user-row count, order-row count, and `orders.user_id` references by rebuilding `users` again without the `status` column or the stricter email constraints.

Limitation: rollback restores the old schema shape, not the original dirty email payloads. The deterministic migrated email values remain in place so rollback stays lossless.

## Postcheck queries to run

Run `postcheck.sql` after the migration. It checks:

- user-row count remains `6`
- order-row count remains `4`
- dirty-user dependent orders still exist for `u4`, `u5`, and `u6`
- cleaned email values match the required deterministic replacements
- no `NULL`, blank, or duplicate emails remain
- `status` exists as `TEXT NOT NULL DEFAULT 'active'`
- `email` is `NOT NULL` and backed by a unique index/constraint
- historical `created_at` values remain unchanged for dirty users

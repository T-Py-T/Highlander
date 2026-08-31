# Migration Report

## Strategy

- Run offline in SQLite inside `BEGIN IMMEDIATE`.
- Disable foreign-key enforcement for the rebuild, rename both `users` and `orders` out of the way, recreate `users` with the new schema, recreate `orders` with the same foreign key back to `users(id)`, copy data forward, then drop the old tables and commit.
- Preserve every `users.id`, `users.name`, `users.created_at`, every `orders.id`, and every `orders.user_id` value by copying rows instead of deleting users or minting new ids.

## Dirty-data cleanup

The migration rewrites only the known dirty email rows, deterministically:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

`u1` keeps `ada@example.com`, which preserves the first valid copy of the duplicated address.

## Idempotency

- The migration always rebuilds `users` from the current `users` table contents.
- The cleanup rules are keyed by stable user ids, so running the script again rewrites `u4`, `u5`, and `u6` to the same final values instead of creating new variants.
- The script drops any leftover `users__migration_old` scratch table before starting, so a clean rerun does not duplicate rows.

## Rollback behavior and limitation

- `rollback.sql` restores the pre-migration `users` schema shape: `id`, `email`, `name`, `created_at`.
- It rebuilds `orders` as well so the foreign key again points at the restored `users` table, while preserving the same user ids, user row count, order row count, and dependent `orders.user_id` references.
- Limitation: rollback restores the old schema shape, not the original dirty email values. The cleaned migrated email values remain in place because the migration intentionally normalizes data before constraints are enforced.

## Postcheck queries to run

Execute `postcheck.sql` after the migration. It checks:

- user and order row counts
- preserved dependent orders for `u4`, `u5`, and `u6`
- exact cleaned email values for dirty users
- preserved `created_at` values for migrated rows
- absence of null, blank, and duplicate emails
- absence of null or non-`active` statuses
- presence of the rebuilt `users` table definition and the generated unique email constraint index
- foreign-key integrity

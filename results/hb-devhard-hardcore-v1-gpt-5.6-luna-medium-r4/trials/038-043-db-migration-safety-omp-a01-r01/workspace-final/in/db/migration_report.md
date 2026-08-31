# Migration Report

## Strategy

`migration.sql` runs in an explicit transaction. It first updates only the known dirty IDs, then rebuilds `users` with `email TEXT NOT NULL UNIQUE` and `status TEXT NOT NULL DEFAULT 'active'`. `created_at` is copied verbatim. SQLite's dependent-table rename behavior is used deliberately: `users` is renamed before rebuilding `orders`, and orders are copied with their original IDs, values, and `user_id` references before either old table is removed.

## Dirty-data cleanup

The retained first `ada@example.com` row (`u1`) is unchanged. Duplicate `u4` becomes `ada+u4@example.com`; null `u5` becomes `missing+u5@example.invalid`; blank `u6` becomes `missing+u6@example.invalid`. These deterministic values preserve all users while satisfying the new constraints.

## Idempotency

The migration does not insert by generated IDs or append rows. Every run deterministically updates the same three IDs and rebuilds each table from its complete current contents, so a second run preserves the same rows and references rather than duplicating them.

## Rollback behavior and limitation

Run `rollback.sql` after the migration. It rebuilds `users` to the old shape (`id`, `email`, `name`, `created_at`) and rebuilds `orders` to preserve its rows and foreign-key references. It intentionally retains the cleaned email values; rollback restores schema shape, not the unknowable pre-migration dirty values. Both rebuilds are transactional.

## Postcheck

Run `postcheck.sql` with SQLite after migration. It checks user/order counts, every expected dependent order reference, deterministic dirty-user emails, invalid email rows, duplicate email groups, null statuses, and the email/status constraints.

# Migration report

## Strategy

`migration.sql` runs with foreign-key enforcement disabled during the controlled parent-table rebuild, inside an explicit transaction. It creates a constrained replacement `users` table, copies every user row, drops only the old parent table, and renames the replacement. `orders` is not rewritten: its rows and `user_id` values remain unchanged. Foreign-key enforcement is restored after commit.

The replacement preserves every `id`, `name`, and historical `created_at`. It adds `status TEXT NOT NULL DEFAULT 'active'` and defines `email TEXT NOT NULL UNIQUE`, enforcing non-null and unique emails for future writes.

## Dirty-data cleanup

The copy is deterministic and documents the cleanup in SQL comments: `u4` becomes `ada+u4@example.com`, `u5` becomes `missing+u5@example.invalid`, and `u6` becomes `missing+u6@example.invalid`. The first `ada@example.com` row (`u1`) is unchanged. No dirty user is deleted.

## Idempotency

The replacement table is dropped if left over from an interrupted prior attempt, and each invocation rebuilds users from the current users rows. Re-running produces the same user ids, cleaned emails, names, timestamps, and active statuses without inserting duplicate users or orders. The transaction prevents a partially rebuilt parent from being committed.

## Rollback limitation and behavior

`rollback.sql` is executable after migration and rebuilds `users` with the old shape: `id`, `email`, `name`, and `created_at`. It preserves the migrated rows and cleaned email values and does not restore the original dirty email text, because that text is intentionally not retained by this migration. It preserves the existing orders and their references. Rollback removes the new status and email constraints, so it is a schema rollback rather than a restoration of discarded dirty values.

## Postcheck

Run `postcheck.sql` after migration. It checks expected user/order counts, all original dependent order/user pairs, the three cleaned dirty-user emails, null/blank and duplicate email counts, status validity/counts, and emits `PRAGMA table_info(users)` and `PRAGMA index_list(users)` for structural verification.

# Migration report

## Strategy
- Run the migration inside an explicit transaction with `BEGIN IMMEDIATE`.
- Temporarily disable foreign-key enforcement during the table rebuild, then re-enable it before commit.
- Rebuild `users` into the target schema instead of dropping data in place.
- Copy all user rows into the rebuilt table, preserving the same `id`, `name`, and `created_at` values.
- Leave `orders` rows in place so each order keeps the same `user_id` reference.

## Dirty-data cleanup
Before a `NOT NULL` + `UNIQUE` email constraint can be enforced for future writes, the existing dirty rows are normalized deterministically:
- `u1` keeps `ada@example.com`.
- `u4` becomes `ada+u4@example.com`.
- `u5` becomes `missing+u5@example.invalid`.
- `u6` becomes `missing+u6@example.invalid`.
- The rebuilt schema also rejects future blank emails with `CHECK (trim(email) <> '')`.

## Resulting schema behavior
- `users.status` is added as `TEXT NOT NULL DEFAULT 'active'`.
- All migrated users receive status `active`.
- `users.email` becomes `TEXT NOT NULL UNIQUE`.
- Historical `created_at` values are preserved.
- Existing orders remain intact and continue to reference the same user ids.

## Idempotency approach
- The migration always rebuilds a fresh `users__migration_new` table from the current `users` contents, then swaps it into place in the same transaction.
- Cleanup values are deterministic, so rerunning the script does not create duplicate users, duplicate orders, or new email variants.
- A second run reproduces the same cleaned user set and keeps the same `id` and `created_at` values.

## Rollback behavior and limitation
- `rollback.sql` rebuilds `users` back to the old schema shape: `id`, `email`, `name`, `created_at`.
- Rollback preserves the same number of users and orders and keeps `orders.user_id` references intact.
- Rollback removes the `status` column and the new email constraints.
- Limitation: rollback restores the old schema shape, not the original dirty email values. The deterministic cleaned email values remain in place because the migration does not keep an out-of-band copy of the pre-cleanup values.

## Postcheck queries to run
Execute `/workspace/in/db/postcheck.sql` after the migration. It verifies:
- total user row count
- total order row count
- preserved dependent order links for `u4`, `u5`, and `u6`
- exact cleaned emails for `u4`, `u5`, and `u6`
- no null or blank emails
- email uniqueness
- presence and shape of the `status` column
- non-null/non-blank status values
- preserved `created_at` values for dirty users
- foreign-key integrity

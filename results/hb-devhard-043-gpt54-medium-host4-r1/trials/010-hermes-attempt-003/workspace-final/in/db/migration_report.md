# Migration report

## Strategy

The migration rebuilds `users` inside an explicit `BEGIN IMMEDIATE ... COMMIT` transaction. It copies every existing user row into a replacement table that adds:

- `status TEXT NOT NULL DEFAULT 'active'`
- `email TEXT NOT NULL UNIQUE CHECK (trim(email) <> '')`

The script preserves every original `users.id`, `users.name`, and `users.created_at` value, then swaps the rebuilt table into place. `orders` rows are preserved as-is, so `orders.user_id` keeps pointing to the same user ids.

## Dirty-data cleanup

The migration applies deterministic email cleanup during the copy step:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

This preserves all legacy users while making the resulting table compatible with future `NOT NULL`, non-blank, and unique email enforcement.

## Idempotency approach

The migration is data-stable on re-run:

- it recreates the target `users` table from the current rows,
- it preserves the same primary keys,
- it does not insert duplicate rows,
- and the cleanup mapping is deterministic, so `u4`, `u5`, and `u6` receive the same migrated emails each time.

## Rollback behavior and limitation

`rollback.sql` restores the pre-migration `users` schema shape (`id`, `email`, `name`, `created_at`) after the migration. It preserves the current user row count, order row count, and all `orders.user_id` references.

Limitation: rollback restores the old schema shape, not the original dirty email values. The cleaned migrated emails remain in place so that no user rows or dependent orders are lost.

## Postcheck queries to run

After applying the migration, run:

1. `sqlite3 <db-file> ".read postcheck.sql"`
2. Confirm:
   - `user_row_count` is `6`
   - `order_row_count` is `4`
   - `orders_for_dirty_users` returns one row each for `u4`, `u5`, and `u6`
   - `dirty_user_emails` shows the expected deterministic migrated values
   - `duplicate_email_count` is `0`
   - `null_or_blank_email_count` is `0`
   - `non_active_status_count` is `0`
   - `PRAGMA foreign_key_check;` returns no rows

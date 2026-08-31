# Migration Report

## Strategy

- Run the migration inside an explicit transaction with foreign keys temporarily disabled during the table swap.
- Copy the current `users` rows into a backup table.
- Rebuild `users` with the new schema: `id`, `email`, `name`, `status`, `created_at`.
- Reinsert every existing user with the original `id`, `name`, and `created_at` so dependent `orders.user_id` values remain valid.
- Replace the old `users` table only after the cleaned data has been inserted successfully.

## Dirty-data cleanup

- Keep the original `ada@example.com` row unchanged for `u1`.
- Rewrite `u4` to `ada+u4@example.com`.
- Rewrite `u5` to `missing+u5@example.invalid`.
- Rewrite `u6` to `missing+u6@example.invalid`.
- The rebuilt schema enforces `email TEXT NOT NULL UNIQUE CHECK (trim(email) <> '')` for future writes.
- The migration sets `status` to `active` for all existing rows and preserves historical `created_at` values.

## Idempotency approach

- The script always rebuilds `users` from the current table contents rather than appending rows, so rerunning it does not duplicate data.
- The cleanup mapping is deterministic, so `u4`, `u5`, and `u6` receive the same migrated email values on every run.
- The temporary migration tables are dropped with `IF EXISTS` before reuse so leftover artifacts do not break a second execution.

## Rollback behavior and limitation

- `rollback.sql` restores the pre-migration `users` schema shape to `id`, `email`, `name`, `created_at`.
- Rollback preserves the same number of users and orders, and keeps the same user ids so order references remain intact.
- Rollback does not recreate the original dirty email values; it keeps the migrated email values while removing the `status` column and email constraints.

## Postcheck queries

Run `postcheck.sql` after the migration to verify:

- user row count remains `6`
- order row count remains `4`
- orders for `u4`, `u5`, and `u6` are still present
- cleaned email values were applied to `u4`, `u5`, and `u6`
- no null, blank, or duplicate emails remain
- the `status` column exists with `NOT NULL` and default `active`

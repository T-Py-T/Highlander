# Migration Report

Date: 2026-08-31

## Strategy

The migration replaces the unsafe `DROP TABLE users` draft with a transactional table rebuild:

1. Disable foreign-key enforcement for the duration of the rebuild.
2. Stage all existing users into `_users_migration_source`.
3. Apply the required deterministic dirty-data cleanup while preserving `id`, `name`, and historical `created_at`.
4. Create the target `users` table with:
   - `email TEXT NOT NULL UNIQUE CHECK (LENGTH(TRIM(email)) > 0)`
   - `status TEXT NOT NULL DEFAULT 'active'`
5. Copy the staged rows into the new table.
6. Swap the rebuilt table into place and commit.

This preserves all six existing users and all four existing orders, including the dependent orders for `u4`, `u5`, and `u6`.

## Dirty-data cleanup

- `u1` remains `ada@example.com`.
- `u4` is rewritten from duplicate `ada@example.com` to `ada+u4@example.com`.
- `u5` is rewritten from `NULL` to `missing+u5@example.invalid`.
- `u6` is rewritten from blank `''` to `missing+u6@example.invalid`.

These cleanup values are deterministic, so rerunning the migration does not create new variants for the same users.

## Idempotency

The migration rebuilds `users` from the current contents each time rather than appending rows, so a second run does not duplicate users or orders. The cleanup mapping is stable for `u4`, `u5`, and `u6`, and the row copy preserves existing `id` and `created_at` values.

## Rollback behavior

`rollback.sql` restores the pre-migration `users` schema shape:

- `id`
- `email`
- `name`
- `created_at`

Rollback preserves the same user-row count and order-row count and keeps `orders.user_id` pointing at the same user ids. It does not restore the original dirty email values; the deterministic cleaned emails remain in place while the schema shape is reverted.

## Postchecks

Run `postcheck.sql` after the migration. It verifies:

- user and order row counts
- cleaned emails for `u4`, `u5`, and `u6`
- preserved dependent orders for dirty users
- absence of duplicate, null, and blank emails
- absence of null or blank statuses
- `users` table definition and indexes
- foreign-key integrity

# Migration Report

## Strategy

`migration.sql` replaces the unsafe drop-only draft with an explicit SQLite transaction that rebuilds `users` into a new table with the target schema, verifies row counts, checks foreign keys, and renames the rebuilt table into place only after the copy succeeds.

## Dirty-data cleanup

The migration preserves every existing `users.id`, every `orders.user_id`, and every historical `created_at` value while applying these deterministic email fixes before enforcing `NOT NULL` and `UNIQUE`:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

The first `ada@example.com` row (`u1`) remains unchanged.

## Idempotency approach

The migration always rebuilds `users` from the current `users` rows into a fresh `users__migration_new` table inside one transaction. Re-running it does not duplicate rows because it copies each current user exactly once and replaces the table atomically. The cleanup mappings are deterministic, so `u4`, `u5`, and `u6` stay on the same migrated addresses across repeated runs.

## Rollback behavior and limitation

`rollback.sql` also runs in an explicit transaction. It restores the pre-migration `users` schema shape to `id`, `email`, `name`, and `created_at`, and preserves all user rows plus all dependent orders.

Rollback is shape-only: it removes the `status` column, but it does not reintroduce the original dirty emails. The cleaned email values remain in place after rollback.

## Post-migration verification

Run `postcheck.sql` after the migration to verify:

- user and order row counts
- preserved orders for `u4`, `u5`, and `u6`
- cleaned email values and populated `status`
- absence of null, blank, or duplicate emails in data
- `email` and `status` `NOT NULL` schema flags
- a unique index backing `users.email`
- no foreign-key violations

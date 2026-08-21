# Migration Report

## Strategy

The migration rebuilds `users` inside an explicit `BEGIN IMMEDIATE` transaction. It copies every existing user into a replacement table with the new schema, then swaps the table name in place. This preserves user ids, keeps `created_at` unchanged, and avoids deleting dependent `orders` rows.

## Dirty-data cleanup

- `u1` keeps `ada@example.com`.
- `u4` is rewritten to `ada+u4@example.com`.
- `u5` is rewritten to `missing+u5@example.invalid`.
- `u6` is rewritten to `missing+u6@example.invalid`.
- Any other unexpected null or blank email would also be rewritten deterministically as `missing+<id>@example.invalid`.

## Idempotency approach

The migration is a full table rebuild from the current `users` contents, so rerunning it does not duplicate rows or create extra users. The cleanup mapping is deterministic by `id`, and the script recreates the constrained target schema on each run.

## Rollback behavior and limitation

`rollback.sql` rebuilds `users` back to the pre-migration schema shape: `id`, `email`, `name`, `created_at`. It preserves the same number of user rows and order rows and keeps the same user ids, so `orders.user_id` references remain valid.

Rollback does not restore the original dirty email values; it restores the old schema shape while keeping the migrated email values already written by the forward migration.

## Postchecks to run

Run `postcheck.sql` after the migration to verify:

- user and order row counts
- dependent order preservation for `u4`, `u5`, and `u6`
- cleaned migrated emails for dirty users
- absence of null, blank, and duplicate emails
- presence of the `status` column and resulting indexes
- foreign key integrity via `PRAGMA foreign_key_check`

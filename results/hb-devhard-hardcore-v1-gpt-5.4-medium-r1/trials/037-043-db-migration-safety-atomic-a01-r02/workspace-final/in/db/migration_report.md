# Migration report

## Strategy

The migration rebuilds `users` inside one explicit transaction. It renames the old table, creates the new constrained table, copies all rows with deterministic email cleanup, swaps the table name back to `users`, and then drops the old copy.

This keeps all 6 user rows, keeps all 4 order rows, preserves every `orders.user_id` reference, and keeps historical `created_at` values.

## Dirty-data cleanup

The copy step applies the required fixed mapping:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

Other rows keep their existing email values.

## New schema behavior

The migrated `users` table adds:

- `status TEXT NOT NULL DEFAULT 'active'`
- `email TEXT NOT NULL UNIQUE`
- `CHECK (length(trim(email)) > 0)` to reject blank emails on future writes

## Idempotency approach

The migration is repeatable. A second run rebuilds the same target `users` table again from the current rows and re-applies the same deterministic cleanup mapping, so it does not duplicate users or break order references.

## Rollback behavior and limit

`rollback.sql` restores the old `users` schema shape: `id`, `email`, `name`, `created_at`.

Rollback preserves user and order row counts and keeps the same user ids referenced by `orders`. It does not restore the old dirty email values; it keeps the cleaned migrated email values while removing the `status` column and the stricter email constraints.

## Postcheck queries

Run `/workspace/in/db/postcheck.sql` after the migration. It checks:

- user and order row counts
- preserved dirty-user order references for `u4`, `u5`, and `u6`
- exact cleaned email values for `u4`, `u5`, and `u6`
- null, blank, and duplicate email violations
- null status violations
- migrated schema details and foreign-key integrity

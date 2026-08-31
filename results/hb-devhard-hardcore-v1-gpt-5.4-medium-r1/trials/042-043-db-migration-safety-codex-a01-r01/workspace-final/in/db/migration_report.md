# Migration Report

## Strategy

The migration rebuilds `users` and `orders` inside one explicit transaction with foreign-key enforcement temporarily disabled during the table swap. This avoids the unsafe draft behavior that dropped `users` without copying data first.

The rebuild sequence is:

1. Create `users__migration_new` with the target schema.
2. Copy all legacy users into the new table while applying deterministic email cleanup and adding `status = 'active'`.
3. Create `orders__migration_new` and copy all existing orders unchanged.
4. Drop legacy `orders`, then legacy `users`.
5. Rename the rebuilt tables into place.
6. Re-enable foreign keys and run `PRAGMA foreign_key_check`.

## Dirty-Data Cleanup

The migration preserves every legacy user row and uses these exact deterministic replacements:

- `u4.email` -> `ada+u4@example.com`
- `u5.email` -> `missing+u5@example.invalid`
- `u6.email` -> `missing+u6@example.invalid`

All other users keep their original `email`, `name`, `id`, and `created_at` values.

## Idempotency

The script is idempotent in the sense required for offline reruns: it rebuilds from the current `users` and `orders` tables into fresh staging tables, then swaps them into place. A second run does not append duplicate users or orders, and the deterministic cleanup keeps the already-migrated dirty rows stable.

## Rollback Behavior

`rollback.sql` restores the old `users` schema shape to:

- `id`
- `email`
- `name`
- `created_at`

It also rebuilds `orders` so foreign-key references remain valid after the rollback.

Rollback limitation: the rollback restores the legacy schema shape, not the original dirty email values. After migration, the cleaned email values remain in place because the migration intentionally normalizes invalid legacy data before enforcing constraints.

## Postcheck Queries

Run `postcheck.sql` after the migration. It verifies:

- user and order row counts
- preserved dependent orders for `u4`, `u5`, and `u6`
- deterministic cleaned emails for dirty users
- absence of null, blank, or duplicate emails
- presence of non-blank `status` values
- foreign-key integrity with `PRAGMA foreign_key_check`

# Migration report

## Strategy
- Run the migration inside `BEGIN IMMEDIATE` / `COMMIT` with foreign keys temporarily disabled during the table swap.
- Rebuild `users` into a new table with the target schema instead of dropping data in place.
- Copy every existing user row forward, preserve every `id`, preserve every `created_at`, and keep `orders.user_id` values unchanged.
- Recreate the final `users` table with `status TEXT NOT NULL DEFAULT 'active'` and a unique email index.

## Dirty-data cleanup
- `u1` keeps `ada@example.com`.
- `u4` is rewritten to `ada+u4@example.com`.
- `u5` is rewritten to `missing+u5@example.invalid`.
- `u6` is rewritten to `missing+u6@example.invalid`.
- The cleanup is deterministic and re-applies the same canonical values on later runs.

## Idempotency approach
- The script always rebuilds the `users` table into a fresh staging table, so rerunning it does not duplicate rows.
- A companion `users__status_shadow` table plus sync triggers preserves `status` values across reruns after the first migration.
- `DROP ... IF EXISTS`, `CREATE ... IF NOT EXISTS`, and fixed email rewrites make the migration repeatable on the same database.

## Rollback behavior and limitation
- Run `rollback.sql` after the migration to restore the old `users` schema shape: `id`, `email`, `name`, `created_at`.
- Rollback preserves user-row count, order-row count, user ids, and dependent order references.
- Rollback intentionally keeps the cleaned email values; it removes the `status` column and migration-side enforcement objects, but it does not reconstruct the original dirty email values.

## Post-migration verification
Run `postcheck.sql` after the migration. It checks:
- user and order row counts,
- preserved dependent orders for `u4`, `u5`, and `u6`,
- the cleaned email values for dirty users,
- absence of duplicate / null / blank emails,
- presence of `status TEXT NOT NULL DEFAULT 'active'`,
- presence of the unique email index and email-required triggers.

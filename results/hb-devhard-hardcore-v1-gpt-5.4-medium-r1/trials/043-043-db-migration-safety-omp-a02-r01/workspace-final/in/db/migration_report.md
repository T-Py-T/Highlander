# Migration Report

## Strategy

The migration rebuilds `users` inside `BEGIN IMMEDIATE ... COMMIT` with `PRAGMA foreign_keys = OFF` during the table swap and `PRAGMA foreign_keys = ON` before commit. It snapshots the original pre-migration `users` rows into `_migration_users_v1_source`, creates a constrained replacement table, copies all users with deterministic email cleanup, then renames the rebuilt table back to `users`.

This preserves:

- all six existing user ids
- all historical `created_at` values
- all four `orders` rows and their existing `user_id` references

## Dirty-data cleanup

The migration rewrites only the known invalid legacy emails:

- `u4`: `ada@example.com` -> `ada+u4@example.com`
- `u5`: `NULL` -> `missing+u5@example.invalid`
- `u6`: `''` -> `missing+u6@example.invalid`

`u1` keeps the original `ada@example.com` value.

## Idempotency approach

The migration is rerunnable because it stores a one-time source snapshot in `_migration_users_v1_source` and always rebuilds `users` from that snapshot. A second execution replays the same deterministic cleanup and table swap without creating duplicate users or duplicate orders.

## Rollback behavior and limitation

`rollback.sql` restores the old `users` table shape to `id, email, name, created_at` after the migration and keeps the same user ids and order references intact. It also removes the migration helper objects `_migration_meta` and `_migration_users_v1_source`.

Limitation: rollback restores the old schema shape, not the original dirty email values. The migrated cleaned emails remain in place because the migration requirement is data preservation, not reintroduction of invalid legacy email states.

## Postcheck queries

Run after migration:

```sql
.read in/db/postcheck.sql
```

The checks cover:

- user row count
- order row count
- dependent order preservation for `u4`, `u5`, and `u6`
- deterministic cleaned email values for dirty users
- absence of null or blank emails
- email uniqueness
- non-null active status values
- presence of `status` and non-null `email` schema constraints
- presence of the unique email index

# Migration report

## Strategy

- Run the migration in an explicit `BEGIN IMMEDIATE` transaction with `PRAGMA foreign_keys = OFF` during the table replacement window.
- Seed a sidecar `users__status_shadow` table before the rebuild so the migration can preserve per-user status values across reruns, even when the source schema is still the legacy four-column shape.
- Rebuild `users` into a new table that enforces `email TEXT NOT NULL UNIQUE` and `status TEXT NOT NULL DEFAULT 'active'`.
- Copy every existing user row into the rebuilt table, preserve `id`, `name`, `created_at`, and load `status` from the sidecar table.
- Recreate triggers after the cutover so later status updates stay mirrored into the sidecar table for a safe second execution.

## Dirty-data cleanup

The migration preserves all legacy users and rewrites only the known dirty emails required by policy:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

`u1` keeps the canonical `ada@example.com` value. User ids stay unchanged, so `orders.user_id` remains attached to the same users.

## Idempotency

- `users__migration_new` is dropped and recreated on each run, so reruns never duplicate user rows.
- `users__status_shadow` stores status by user id outside the rebuilt `users` table, which lets the migration preserve current status values when it runs again.
- The second execution repeats the same deterministic email cleanup for `u4`, `u5`, and `u6`, so reruns do not drift those values.

## Rollback behavior and limitation

- `rollback.sql` restores the old `users` schema shape: `id`, `email`, `name`, `created_at`.
- Rollback also removes the migration sidecar triggers and `users__status_shadow` table.
- Rollback preserves the migrated user rows and dependent orders, but it does not restore the original dirty email values. The cleaned email values remain, because reversing them would intentionally reintroduce the duplicate/null/blank data that the migration removed.

## Post-migration verification

Run these after applying `migration.sql`:

```sh
sqlite3 <database-file> ".read in/db/postcheck.sql"
```

`postcheck.sql` checks:

- total user and order row counts
- dependent order preservation for `u4`, `u5`, and `u6`
- exact cleaned email values for the dirty users
- exact historical `created_at` preservation
- `email` non-null enforcement
- `status` non-null/default enforcement
- unique email enforcement and absence of blank/null/duplicate email values

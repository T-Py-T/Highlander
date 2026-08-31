# Migration Report

## Strategy

The migration rebuilds `users` inside an explicit transaction after temporarily disabling foreign key enforcement. It snapshots the original user rows into `users__migration_source`, drops and recreates `users` under the same table name with the new `status` column and stricter email constraints, copies all rows back with deterministic email cleanup, and then drops the temporary source table before commit.

This preserves:

- all existing user ids
- all existing order rows
- all `orders.user_id` references
- all historical `created_at` values

## Dirty-Data Cleanup

The migration preserves every user row and applies the required deterministic replacements:

- `u4`: `ada@example.com` -> `ada+u4@example.com`
- `u5`: `NULL` -> `missing+u5@example.invalid`
- `u6`: `''` -> `missing+u6@example.invalid`

`u1` keeps `ada@example.com` unchanged.

## Constraint Outcome

After the rebuild, `users` enforces:

- `email TEXT NOT NULL`
- `UNIQUE(email)`
- `CHECK (trim(email) <> '')`
- `status TEXT NOT NULL DEFAULT 'active'`

This rejects future duplicate, null, and blank email writes.

## Idempotency Approach

The script is deterministic: each run rebuilds `users` from the current rows using the same fixed cleanup mapping and reuses the same user ids and `created_at` values. Running it a second time does not duplicate rows or change the cleaned email outputs.

## Rollback Behavior And Limitation

`rollback.sql` restores the pre-migration `users` schema shape:

- `id`
- `email`
- `name`
- `created_at`

Rollback preserves the same user rows and order rows, but it only restores the old schema shape. It does not recreate the original dirty email values because the migrated email values are retained when copying data back into the old four-column table.

## Postcheck Queries

Run `postcheck.sql` after the migration to verify:

- user and order row counts
- preserved orders for `u4`, `u5`, and `u6`
- cleaned emails for `u4`, `u5`, and `u6`
- absence of null, blank, and duplicate emails
- presence of non-null `status`
- table shape via `PRAGMA table_info(users)`
- valid foreign keys via `PRAGMA foreign_key_check`

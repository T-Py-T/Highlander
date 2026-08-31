# Migration report

## Strategy

The migration rebuilds `users` inside an explicit transaction with foreign keys temporarily disabled, then restores enforcement after the copy.

It preserves:

- every existing user id
- every existing order row
- every `orders.user_id` reference
- every historical `created_at` value

It adds:

- `users.status TEXT NOT NULL DEFAULT 'active'`
- unique email enforcement through `users_email_unique_idx`
- non-null and non-blank email enforcement for future inserts and updates through triggers

## Dirty-data cleanup

The migration keeps all dirty users and rewrites only their unsafe email values:

- `u4`: `ada@example.com` -> `ada+u4@example.com`
- `u5`: `NULL` -> `missing+u5@example.invalid`
- `u6`: `''` -> `missing+u6@example.invalid`

The script also includes defensive fallback cleanup for any other null, blank, or later duplicate `ada@example.com` row by deriving a deterministic value from the user id.

## Idempotency approach

The script stores a one-time `users__rollback_backup` table with the pre-migration user shape, then rebuilds `users` from the current rows.

Running the migration again:

- does not duplicate users
- does not duplicate orders
- keeps the same user ids
- keeps the same cleaned email values for `u4`, `u5`, and `u6`
- recreates the same index and triggers

## Rollback behavior and limit

`rollback.sql` restores the old `users` schema shape:

- `id`
- `email`
- `name`
- `created_at`

It rebuilds `users` from `users__rollback_backup`, so it restores the original pre-migration email values, including the dirty legacy values. Order rows remain in place and still point to the same user ids.

The rollback script assumes the migration already created `users__rollback_backup`.

## Postchecks to run

Run `postcheck.sql` after the migration. It checks:

- user row count preservation
- order row count preservation
- dependent order preservation for `u4`, `u5`, and `u6`
- exact cleaned email values for the dirty users
- presence and validity of the `status` column
- non-null, non-blank, and unique email state
- presence of the email index and enforcement triggers

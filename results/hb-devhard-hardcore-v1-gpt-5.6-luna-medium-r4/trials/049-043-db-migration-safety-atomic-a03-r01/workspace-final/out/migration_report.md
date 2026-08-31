# SQLite users migration report

## Strategy

`migration.sql` disables foreign-key enforcement before its explicit `BEGIN IMMEDIATE` transaction, builds a constrained replacement table, copies every user while retaining ids, names, and historical `created_at` text, swaps the table, commits, and enables foreign keys again. The orders table is not rewritten, so every order and `orders.user_id` value remains unchanged. Validation includes `PRAGMA foreign_key_check` after the swap.

The replacement schema makes `email` both `NOT NULL` and `UNIQUE` and adds `status TEXT NOT NULL DEFAULT 'active'`. Existing users receive `active`; future inserts that omit status receive the same default, while explicit NULL status values fail.

## Email cleanup

The copy changes only the policy-listed dirty users:

- `u4`: `ada@example.com` -> `ada+u4@example.com`
- `u5`: NULL -> `missing+u5@example.invalid`
- `u6`: the empty string -> `missing+u6@example.invalid`

User `u1` remains `ada@example.com`, and all other email text is copied verbatim.

## Idempotency

Every run reconstructs the same constrained users table from the current rows and applies the same id-based cleanup. Running the migration again on its own output therefore preserves users, orders, references, timestamps, emails, and active statuses without creating duplicate objects or rows.

## Rollback behavior and limitation

`rollback.sql` uses another transactional table swap to restore the users columns, in order, to `id`, `email`, `name`, `created_at`. It copies the migrated ids, emails, names, and timestamps and leaves all orders untouched.

Rollback removes the status column and preserves the cleaned email values. It cannot recover the original duplicate, NULL, or blank emails because the migration intentionally does not retain a backup of those dirty values. This is the rollback limitation.

## Postcheck use

Execute `postcheck.sql` against the migrated database. It returns one row per check with `check_name`, integer `passed`, and `details`. Success requires every `passed` value to be `1`. The checks cover the 6 user and 4 order counts, dirty-user order dependencies, exact cleaned emails, email NOT NULL/UNIQUE metadata, status type/NOT NULL/default and migrated values, and foreign-key integrity. The SQL only reads database state.

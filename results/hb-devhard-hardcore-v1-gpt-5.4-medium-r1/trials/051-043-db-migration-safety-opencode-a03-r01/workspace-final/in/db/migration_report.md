# Migration Report

## Strategy

The migration rebuilds `users` inside an explicit transaction instead of mutating rows in place or dropping user data. It:

1. disables foreign-key enforcement temporarily,
2. creates a replacement `users` table with `email TEXT NOT NULL UNIQUE` and `status TEXT NOT NULL DEFAULT 'active'`,
3. copies every existing user row into the new table while preserving `id`, `name`, and historical `created_at`,
4. applies deterministic cleanup for known dirty emails,
5. swaps the rebuilt table into place, and
6. runs `PRAGMA foreign_key_check` before commit.

Because user ids are preserved exactly, dependent `orders.user_id` references remain attached to the same users.

## Dirty-data cleanup

The migration applies the required email fixes exactly:

| user_id | old email | new email |
| --- | --- | --- |
| `u4` | `ada@example.com` | `ada+u4@example.com` |
| `u5` | `NULL` | `missing+u5@example.invalid` |
| `u6` | `''` | `missing+u6@example.invalid` |

`u1` keeps `ada@example.com` unchanged so the original canonical address is preserved.

## Idempotency approach

The script is written as a full table rebuild from the current `users` contents. Re-running it does not duplicate rows and re-applies the same deterministic cleanup values for `u4`, `u5`, and `u6`, so the resulting dataset remains stable.

## Rollback behavior and limitation

`rollback.sql` restores the pre-migration `users` schema shape to:

- `id`
- `email`
- `name`
- `created_at`

It preserves all user rows and all order rows, including orders for `u4`, `u5`, and `u6`, because ids are not changed. The rollback restores the old schema shape, not the old dirty email values.

## Post-migration verification

Run `postcheck.sql` after the migration. It verifies:

- user and order row counts,
- preserved dependent orders for `u4`, `u5`, and `u6`,
- exact cleaned email values for dirty users,
- absence of null or blank emails,
- absence of duplicate emails,
- non-null active status values, and
- foreign-key integrity via `PRAGMA foreign_key_check`.

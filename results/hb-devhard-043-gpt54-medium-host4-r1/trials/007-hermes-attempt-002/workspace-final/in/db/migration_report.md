# Migration report

## Strategy

The migration rebuilds `users` inside an explicit transaction, copies every existing user row into a new constrained table, and then swaps the rebuilt table into place. This avoids dropping any user rows and keeps `orders.user_id` pointing at the same user ids because the migration preserves every `users.id` value.

## Dirty-data cleanup

The migration applies deterministic email cleanup before enforcing `NOT NULL` and `UNIQUE` on `users.email`:

- `u1` stays `ada@example.com`.
- `u4` becomes `ada+u4@example.com`.
- `u5` becomes `missing+u5@example.invalid`.
- `u6` becomes `missing+u6@example.invalid`.
- Any other unexpected `NULL` or blank email is converted to `missing+<id>@example.invalid`.

Historical `created_at` values are copied through unchanged, and the new `status` column is populated as `active` for migrated rows.

## Idempotency approach

The migration is rerunnable because it always rebuilds `users` from the current table contents inside a transaction, writes one output row per existing user id, and swaps tables only after the copy succeeds. Re-running the script does not duplicate users or orders, and it reapplies the same deterministic cleanup values for `u4`, `u5`, and `u6`.

## Rollback behavior and limitation

`rollback.sql` restores the pre-migration `users` schema shape (`id`, `email`, `name`, `created_at`) after the migration and preserves the same user ids and order rows. It intentionally does not reintroduce the original dirty email values, so cleaned email addresses remain cleaned after rollback; rollback removes the `status` column and future-write email constraints, but it is schema rollback rather than data-dirtiness rollback.

## Postcheck queries to run

Run the verification queries after migration with:

```sh
sqlite3 your.db < postcheck.sql
```

`postcheck.sql` verifies:

- user and order row counts,
- absence of orphaned orders,
- exact cleaned emails for `u4`, `u5`, and `u6`,
- absence of remaining null/blank or duplicate emails,
- absence of null `status` values,
- user table definition and foreign-key integrity.

# Preflight report

## Dirty email findings before migration

Source dataset: `schema.sql`

- Duplicate email: `ada@example.com` appears on users `u1` and `u4`.
- Null email: user `u5` has `NULL` email.
- Blank email: user `u6` has `''` email.
- Dirty-user count: 3 (`u4`, `u5`, `u6`).
- Total user rows before migration: 6.
- Total order rows before migration: 4.

## Dependent orders tied to dirty users

- `u4` has order `o2` (`total_cents = 4599`, `created_at = 2024-04-02T10:30:00Z`).
- `u5` has order `o3` (`total_cents = 799`, `created_at = 2024-04-03T11:45:00Z`).
- `u6` has order `o4` (`total_cents = 1599`, `created_at = 2024-04-04T12:10:00Z`).

## Required cleanup mapping

- Preserve `u1` as the canonical `ada@example.com` row.
- Rewrite duplicate user `u4` email to `ada+u4@example.com`.
- Rewrite null email user `u5` to `missing+u5@example.invalid`.
- Rewrite blank email user `u6` to `missing+u6@example.invalid`.
- Preserve all user ids, all order ids, and every `orders.user_id` reference.
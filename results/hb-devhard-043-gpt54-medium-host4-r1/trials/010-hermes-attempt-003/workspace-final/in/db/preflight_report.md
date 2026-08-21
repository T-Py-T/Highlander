# Preflight report

Source: `schema.sql`

## Dirty email findings before migration

Users table contains 6 rows. The following rows violate the target email rules (`NOT NULL`, non-blank, unique):

- `u4` duplicates `u1` on `ada@example.com`.
- `u5` has `NULL` email.
- `u6` has a blank email (`''`).

## Dependent orders that must be preserved

Dirty users have existing dependent orders and therefore cannot be dropped or replaced with new ids:

- `u4` -> order `o2`
- `u5` -> order `o3`
- `u6` -> order `o4`

These orders must remain present after migration and must still reference the same user ids (`u4`, `u5`, `u6`).

## Planned deterministic cleanup

- Keep `u1` unchanged as `ada@example.com`.
- Rewrite `u4` email to `ada+u4@example.com`.
- Rewrite `u5` email to `missing+u5@example.invalid`.
- Rewrite `u6` email to `missing+u6@example.invalid`.
- Preserve all `created_at` values.
- Add `status TEXT NOT NULL DEFAULT 'active'` for all migrated rows and future inserts.

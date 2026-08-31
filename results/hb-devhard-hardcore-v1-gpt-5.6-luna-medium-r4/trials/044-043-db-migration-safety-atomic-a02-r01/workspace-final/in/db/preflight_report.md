# Preflight report

## Findings before migration

The existing `users` data contains email values that cannot satisfy the new
constraints:

- `u1` and `u4` both have `ada@example.com` (duplicate). `u1` is the first
  existing row and remains unchanged.
- `u5` has a `NULL` email.
- `u6` has a blank email (`''`).

Dirty users also have dependent orders that must remain attached by user id:
`o2` references `u4`, `o3` references `u5`, and `o4` references `u6`.

## Planned cleanup

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

The migration copies orders before replacing the users table, so these
references and all other order rows remain intact.

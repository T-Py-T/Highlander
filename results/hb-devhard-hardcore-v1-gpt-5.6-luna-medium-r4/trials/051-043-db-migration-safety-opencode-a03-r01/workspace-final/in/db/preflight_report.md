# Preflight Report

The legacy `users.email` column is nullable and has no uniqueness constraint.
The pre-migration data contains these issues:

- `u4` duplicates the existing `ada@example.com` address on `u1`.
- `u5` has a `NULL` email address.
- `u6` has a blank email address (`''`).

Dirty users also have dependent orders that must remain attached to the same
user IDs:

- `u4`: order `o2`
- `u5`: order `o3`
- `u6`: order `o4`

The migration resolves the dirty values deterministically before adding the
non-null unique constraint: `u4` becomes `ada+u4@example.com`, `u5` becomes
`missing+u5@example.invalid`, and `u6` becomes
`missing+u6@example.invalid`.

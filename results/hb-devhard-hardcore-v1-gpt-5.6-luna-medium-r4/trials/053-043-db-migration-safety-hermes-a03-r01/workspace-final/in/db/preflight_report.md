# Preflight report

Source schema: `users` permits NULL and duplicate email values, so the new
non-null/unique constraint cannot be added in place without cleanup.

Findings before migration:

- `ada@example.com` is duplicated: `u1` and `u4`. Per policy, `u1` is the
  first existing row and remains unchanged; `u4` is the dirty duplicate.
- `u5` has a NULL email.
- `u6` has a blank email (`''`).
- Dirty users therefore include `u4`, `u5`, and `u6`.
- Dependent orders exist for all three dirty users: `o2.user_id = 'u4'`,
  `o3.user_id = 'u5'`, and `o4.user_id = 'u6'`. Their rows and references must
  remain unchanged.

The migration resolves these conflicts deterministically: `u4` becomes
`ada+u4@example.com`, `u5` becomes `missing+u5@example.invalid`, and `u6`
becomes `missing+u6@example.invalid`.

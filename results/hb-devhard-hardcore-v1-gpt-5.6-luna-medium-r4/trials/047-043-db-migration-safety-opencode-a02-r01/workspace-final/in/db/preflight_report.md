# Preflight Report

The source schema permits nullable, non-unique emails. Before migration:

- `u1` and `u4` both use `ada@example.com`; `u4` is the duplicate that must be cleaned.
- `u5` has a `NULL` email.
- `u6` has a blank email (`''`).
- Dirty users `u4`, `u5`, and `u6` have dependent orders `o2`, `o3`, and `o4`, respectively. Their `user_id` values must remain unchanged.

The migration preserves every user and order, then assigns deterministic unique
emails before installing the new constraints.

# Preflight Report

## Dirty Email Findings Before Migration

- Duplicate email: `ada@example.com` is used by `u1` and `u4`.
- Null email: `u5` has `email = NULL`.
- Blank email: `u6` has `email = ''`.

## Required Deterministic Cleanup

- Keep `u1` unchanged as `ada@example.com`.
- Update `u4` to `ada+u4@example.com`.
- Update `u5` to `missing+u5@example.invalid`.
- Update `u6` to `missing+u6@example.invalid`.

## Dependent Orders That Must Be Preserved

- `u4` has dependent order `o2`.
- `u5` has dependent order `o3`.
- `u6` has dependent order `o4`.

## Preservation Requirements

- Preserve all 6 existing user rows.
- Preserve all 4 existing order rows.
- Preserve `orders.user_id` references to `u4`, `u5`, and `u6`.
- Preserve each user's historical `created_at` value.

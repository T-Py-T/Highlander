# Preflight Report

The source `users` data contains six rows. `u1` and `u4` both have
`ada@example.com`, so `u4` is a duplicate. `u5` has a NULL email and `u6` has
a blank email. The source also contains dependent orders for every dirty user:
`o2` references `u4`, `o3` references `u5`, and `o4` references `u6`.

The migration must therefore clean values by user id rather than delete or
merge users: `u4` becomes `ada+u4@example.com`, `u5` becomes
`missing+u5@example.invalid`, and `u6` becomes
`missing+u6@example.invalid`. Their orders must retain the same order ids and
`user_id` references.

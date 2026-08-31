# Interface Fix Report

## Root Cause

`catalog.Product` now exposes `price` as a `Money` object containing
`amount_cents` and `currency`. The orders adapter still read the removed
`price_cents` and top-level `currency` attributes, so orders using current
catalog products failed before reports could aggregate them.

## Changes

- `packages/orders/orders/adapter.py`
  - Reads `Money.amount_cents` and `Money.currency` from current products.
  - Retains support for legacy dictionaries containing `price_cents` and
    `currency`.
- `packages/orders/orders/service.py`
  - Keeps currency validation and reports both currencies in the mixed-currency
    error message.

The `Money` model and the reports output contract were preserved. No fixture
values or third-party dependencies were added.

## Verification

Requested command:

```text
python -m pytest tests
```

It could not run in this environment because `python` is unavailable and
`python3` has no installed `pytest` module.

Successful checks:

- `python3 -m compileall -q packages`
- Manual checks for current `Money` products, legacy `price_cents` dictionaries,
  report aggregation, and mixed-currency rejection.

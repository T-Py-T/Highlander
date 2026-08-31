# Interface Fix Report

## Root Cause

`catalog` now exposes a product's price as `product.price`, a `Money` object whose fields are `amount_cents` and `currency`. `orders.adapter` still read the removed `product.price_cents` and top-level `product.currency` attributes, so current catalog products could not be priced. The adapter also needed to continue accepting legacy dictionaries with `price_cents`.

## Changed Files

- `packages/orders/orders/adapter.py`: read `Money.amount_cents` and `Money.currency` for current products, while retaining the legacy dictionary path.
- `packages/orders/orders/service.py`: preserve mixed-currency rejection and include both currencies in the error for clarity.

The `catalog` `Money` model and the reports aggregation contract were left unchanged.

## Verification

Requested command:

```text
python -m pytest tests
```

It could not run in this environment because `python` is unavailable. The equivalent `python3 -m pytest tests` also could not run because `pytest` is not installed. A direct `python3` integration check with `PYTHONPATH=packages/catalog:packages/orders:packages/reports` passed for current `Money` products, legacy dictionaries, per-currency reports, and mixed-currency rejection.

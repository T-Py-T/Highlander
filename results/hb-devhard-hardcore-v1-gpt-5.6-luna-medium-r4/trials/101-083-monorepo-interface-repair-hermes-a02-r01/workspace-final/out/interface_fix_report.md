# Interface Fix Report

## Root cause

`catalog` now exposes product prices as `Product.price`, a `Money` object containing `amount_cents` and `currency`. `orders.adapter.price_cents()` still attempted to read `product.price_cents` for non-dictionary products, so current `catalog` `Product` instances failed at the orders boundary. The adapter also did not read currency from the new `Money` object; this could incorrectly fall back to USD.

## Changes

- `packages/orders/orders/adapter.py`
  - Added boundary handling for the new `Product.price.amount_cents` and `Product.price.currency` interface.
  - Preserved support for legacy dictionaries containing `price_cents`, including string values that are converted to integers as before.
  - Preserved legacy dictionary currency handling and the USD default when no legacy currency is supplied.
  - Kept currency values intact so `orders.service.price_order()` continues to reject mixed-currency orders with `ValueError("mixed currencies are not supported")`.
- No test files were modified.
- The `catalog.Money` model was not removed or flattened.

## Verification

The requested command was:

```text
python -m pytest tests
```

In this execution environment, the initial attempt could not run because the system Python did not have pytest installed (`No module named pytest`). The equivalent dependency-isolated verification command was then run successfully:

```text
uv run --with pytest pytest tests
```

Result: **5 passed**.

Additional runtime checks verified both a legacy `price_cents` dictionary and a `Money` product, plus rejection of a mixed-currency order. Result: **legacy, Money, and mixed-currency checks passed**.

# Interface Fix Report

## Root cause

The `catalog` package now exposes product prices as `Product.price`, a `Money` object containing `amount_cents` and `currency`. The `orders` adapter still read `product.price_cents` and read the currency directly from `product`, so catalog `Product` instances failed at the orders boundary. The legacy dictionary path remained supported through its `price_cents` field.

## Changes

- Updated `packages/orders/orders/adapter.py`.
- `price_cents()` now adapts the new `Product.price.amount_cents` shape while retaining support for legacy dictionaries containing `price_cents`.
- `currency()` now reads the currency from `Product.price.currency` for the new model and retains legacy dictionary compatibility.
- `orders.service.price_order()` and `reports.monthly.summarize_orders()` were left structurally unchanged: order-level currency checking still raises `ValueError("mixed currencies are not supported")`, and reports continue grouping totals by currency.
- No tests or third-party dependencies were modified.

## Verification

Command:

```text
python -m pytest tests
```

In this execution environment, `pytest` was not installed in the system Python, so the command was run through the equivalent isolated runner:

```text
uv run --with pytest python -m pytest tests
```

Result: **5 passed**.

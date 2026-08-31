# Interface Fix Report

## Root cause
`catalog` migrated product pricing from a legacy `price_cents` field to `Product.price: Money(amount_cents, currency)`, but `orders.adapter` still read `product.price_cents` / `product["price_cents"]` and only guessed currency from top-level fields. That broke downstream order pricing for `catalog.Product` objects and left currency handling split across incompatible shapes.

## Changed files
- `packages/orders/orders/adapter.py`
  - Added `_price_data(product)` as the boundary adapter for both supported product shapes.
  - Reads new `Money` pricing from object or dictionary `price` values.
  - Preserves legacy dictionary support for `price_cents` plus top-level `currency`.
- `packages/orders/orders/service.py`
  - Kept mixed-currency validation in the order layer.
  - Improved the raised error to name both conflicting currencies.

## Verification command
Executed from `/workspace/in/shopmono` with a temporary local shim for missing host tools:

`python -m pytest tests`

Result: `5 passed`

Additional smoke check: legacy product dictionaries still return `300 USD` through `orders.adapter.price_cents()` / `orders.adapter.currency()`.

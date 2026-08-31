# Interface Fix Report

## Root cause
`catalog` migrated product pricing from the legacy `price_cents` scalar to `Product.price`, a `Money(amount_cents, currency)` object. The downstream `orders` adapter still assumed every non-dict product exposed `price_cents` and `currency` directly on the product object, so cross-package calls broke once `catalog.sample_catalog()` started returning `Product(price=Money(...))` instances.

## Changed files
- `/workspace/in/shopmono/packages/orders/orders/adapter.py`
  - Added a boundary adapter helper that normalizes both supported product shapes:
    - new catalog objects with `price.amount_cents` and `price.currency`
    - legacy product dictionaries with `price_cents` and `currency`
  - Updated `price_cents(product)` to read cents from either normalized shape.
  - Updated `currency(product)` to read currency from either normalized shape.

## Behavior preserved
- The new `catalog` `Money` model remains intact.
- Legacy product dictionaries containing `price_cents` are still supported.
- Mixed currencies in a single order are still rejected by `orders.service.price_order` with a clear `ValueError` containing `mixed`.

## Verification command
`uv run --with pytest python3 -m pytest tests`

## Verification result
Passed: `5 passed in 0.03s`

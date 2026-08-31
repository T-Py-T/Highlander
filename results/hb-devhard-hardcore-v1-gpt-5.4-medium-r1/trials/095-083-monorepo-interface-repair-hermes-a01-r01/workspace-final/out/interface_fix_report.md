# Interface Repair Report

## Root cause
`catalog` migrated product prices from a legacy flat `price_cents` field to a nested `Money(amount_cents, currency)` object on `Product.price`.

`orders.adapter` still assumed the old interface:
- `price_cents(product)` tried to read `product.price_cents`
- `currency(product)` looked for a top-level `currency`

That broke cross-package consumers when `orders.service` and `reports.monthly` received catalog `Product` objects using the new `Money` model.

## Changed files
- `packages/orders/orders/adapter.py`
  - Added a boundary adapter helper that accepts both:
    - new products exposing `price` as a `Money`-like object
    - legacy dictionaries exposing `price_cents`
  - `price_cents(product)` now reads `price.amount_cents` for new models and still supports legacy values.
  - `currency(product)` now reads `price.currency` for new models and preserves legacy dictionary behavior.
- `packages/orders/orders/service.py`
  - Kept mixed-currency validation intact.
  - Improved the error message to clearly state the conflicting currencies in a single order.

## Verification command
From the repo root:

```bash
uv run --with pytest pytest tests
```

## Verification result
All tests passed after the fix.

## Root cause

`catalog` now exposes product pricing as `Product.price: Money(amount_cents, currency)`, but `orders.adapter` still assumed the legacy interface and read `product.price_cents` and `product.currency` directly. That broke cross-package calls from `orders` and `reports` when they received `catalog.Product` instances.

## Changed files

- `packages/orders/orders/adapter.py`
  - Updated `price_cents(product)` to support both:
    - new `Product(price=Money(...))` objects
    - legacy product dictionaries with `price_cents`
  - Updated `currency(product)` to read currency from `Money.currency` for new products while preserving legacy dictionary support.

## Verification

Requested command:

```bash
python -m pytest tests
```

Environment note:

- The provided container does not have `python`/`pytest` available for that exact command.
- Direct behavioral verification was run with `python3` and `PYTHONPATH=packages/catalog:packages/orders:packages/reports`, covering:
  - `Money`-backed product pricing
  - legacy product dictionary pricing
  - order totals
  - revenue grouping by currency
  - mixed-currency order rejection with a clear `ValueError`

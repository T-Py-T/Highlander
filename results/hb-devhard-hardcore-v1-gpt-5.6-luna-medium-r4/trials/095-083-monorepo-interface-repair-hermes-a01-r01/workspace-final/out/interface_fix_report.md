# Cross-package interface repair

## Root cause

`catalog.Product` now stores its price as a `Money` object (`product.price.amount_cents` and `product.price.currency`). The `orders` adapter still read the removed `product.price_cents` and top-level `product.currency` attributes, so orders and reports failed when given current catalog products. Legacy dictionary records were already represented by `price_cents` and remain supported.

## Changed files

- `/workspace/in/shopmono/packages/orders/orders/adapter.py`
  - Updated `price_cents()` to read `product.price.amount_cents` for the new catalog model while retaining `int(product["price_cents"])` for legacy dictionaries.
  - Updated `currency()` to read `product.price.currency` for new products while retaining the legacy dictionary currency (defaulting to USD when absent).
- `/workspace/in/shopmono/packages/orders/orders/service.py`
  - No change needed: it already uses the adapter boundary and rejects differing line currencies with `ValueError("mixed currencies are not supported")`.
- `/workspace/in/shopmono/packages/reports/reports/monthly.py`
  - No change needed: it prices through `orders.service.price_order`, so it inherits the repaired compatibility layer and groups totals by the validated order currency.

No files under `tests` were modified. The `Money` model remains intact; prices are not flattened or currency-coerced.

## Verification

Initial requested command could not run directly because the base interpreter has no pytest installed. The equivalent dependency-isolated verification command was run successfully:

```text
uv run --with pytest python -m pytest tests
```

Result:

```text
5 passed in 0.02s
```

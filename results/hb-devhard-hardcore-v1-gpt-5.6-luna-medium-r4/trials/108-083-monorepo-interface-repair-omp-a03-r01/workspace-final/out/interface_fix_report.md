# Interface Fix Report

## Root cause

`catalog` products now expose `price` as a `Money` object, whose amount is stored in `amount_cents` and whose currency is stored in `currency`. `orders.adapter` still read `product.price_cents` for non-dictionary products and therefore failed on the new `Product` model. Its currency lookup also only checked a top-level product attribute, rather than the nested `Money` value.

## Changed files

- `packages/orders/orders/adapter.py`
  - Read amounts from `Product.price.amount_cents` for the new catalog model.
  - Read currencies from `Product.price.currency`.
  - Continue accepting legacy dictionaries with `price_cents` and top-level `currency`.
  - Also support dictionary records carrying a nested `price` value.
  - Retain legacy object attribute fallbacks.
- `packages/orders/orders/service.py` and `packages/reports/reports/monthly.py` required no source changes: they consume the adapter boundary and preserve integer totals grouped by currency.

No files under `tests` were modified. The `Money` model remains intact, and order pricing still raises `ValueError("mixed currencies are not supported")` when an order contains different currencies.

## Verification command

Requested command:

```text
python -m pytest tests
```

It could not execute in this environment because `python` is unavailable. The equivalent `python3 -m pytest tests` also could not execute because the environment has no `pytest` module.

Available verification completed successfully:

```text
PYTHONPATH=packages/catalog:packages/orders:packages/reports python3 -m compileall -q packages
```

A direct Python smoke scenario also passed for new `Money` products, legacy `price_cents` dictionaries, report currency grouping, and mixed-currency rejection.

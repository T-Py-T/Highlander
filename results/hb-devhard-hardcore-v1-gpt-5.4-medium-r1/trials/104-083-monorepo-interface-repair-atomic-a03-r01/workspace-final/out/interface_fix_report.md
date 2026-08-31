# Interface Fix Report

## Root cause
`catalog` moved product prices from a top-level `price_cents` field to `price: Money(amount_cents, currency)`.

`orders.adapter` still assumed the old shape:
- `price_cents(product)` read `product.price_cents` or `dict['price_cents']`
- `currency(product)` read top-level `currency`

That broke cross-package use with new `catalog.Product` objects and also hid non-USD currencies stored under `product.price.currency`.

## Changed files
- `/workspace/in/shopmono/packages/orders/orders/adapter.py`

## What changed
Updated the `orders` adapter boundary to support both interfaces:
- new objects with `price.amount_cents` and `price.currency`
- dicts with nested `price`
- legacy dicts with `price_cents` and top-level `currency`

This keeps the `Money` model in `catalog`, preserves legacy product dict support, and lets existing mixed-currency validation in `orders.service` keep raising `ValueError("mixed currencies are not supported")`.

## Verification
Primary command:
```bash
cd /workspace/in/shopmono && python3 -m pytest tests
```

The current container image does not have the `pytest` module installed, so I verified behavior with a direct Python run using the package paths:
```bash
cd /workspace/in/shopmono && PYTHONPATH=packages/catalog:packages/orders:packages/reports python3 - <<'PY'
from catalog.pricing import sample_catalog
from orders.service import price_order
from reports.monthly import summarize_orders

catalog = sample_catalog()
assert price_order([{'sku': 'PEN', 'quantity': 2}, {'sku': 'PAD', 'quantity': 1}], catalog) == {'total_cents': 550, 'currency': 'USD'}
assert summarize_orders([
    {'id': 'o1', 'lines': [{'sku': 'PEN', 'quantity': 2}]},
    {'id': 'o2', 'lines': [{'sku': 'MUG', 'quantity': 1}]},
], catalog) == {'order_count': 2, 'revenue_by_currency': {'USD': 250, 'EUR': 700}}
try:
    price_order([{'sku': 'PEN', 'quantity': 1}, {'sku': 'MUG', 'quantity': 1}], catalog)
except ValueError as exc:
    assert 'mixed' in str(exc)
else:
    raise AssertionError('expected mixed-currency order to fail')
PY
```

# Interface Fix Report

## Root Cause

`catalog` migrated product pricing from a flat `price_cents` field to `Product.price: Money(amount_cents, currency)`, but `orders.adapter` still read `product.price_cents` and `product.currency` directly. That broke cross-package compatibility for new catalog `Product` objects while downstream code still needed to accept legacy product dictionaries containing `price_cents`.

## Changed Files

- `packages/orders/orders/adapter.py`
  - Updated `price_cents(product)` to support:
    - new object shape: `product.price.amount_cents`
    - new dictionary shape: `product["price"]["amount_cents"]`
    - legacy dictionary shape: `product["price_cents"]`
    - legacy object fallback: `product.price_cents`
  - Updated `currency(product)` to support:
    - new object shape: `product.price.currency`
    - new dictionary shape: `product["price"]["currency"]`
    - legacy dictionary shape: `product["currency"]` with existing USD default behavior
    - legacy object fallback: `product.currency`

## Verification

Expected repo test command:

```bash
python -m pytest tests
```

Environment note:

- In this execution environment, `python` was not installed and `python3 -m pytest tests` also failed because `pytest` is not available.
- Functional verification was performed with:

```bash
PYTHONPATH=packages/catalog:packages/orders:packages/reports python3 - <<'PY'
from catalog.pricing import sample_catalog
from orders.service import price_order
from reports.monthly import summarize_orders
from catalog.models import Money, Product
from orders.adapter import currency, price_cents

catalog = sample_catalog()
assert price_order([{"sku": "PEN", "quantity": 2}, {"sku": "PAD", "quantity": 1}], catalog) == {
    "total_cents": 550,
    "currency": "USD",
}
assert summarize_orders(
    [
        {"id": "o1", "lines": [{"sku": "PEN", "quantity": 2}]},
        {"id": "o2", "lines": [{"sku": "MUG", "quantity": 1}]},
    ],
    catalog,
) == {"order_count": 2, "revenue_by_currency": {"USD": 250, "EUR": 700}}
try:
    price_order([{"sku": "PEN", "quantity": 1}, {"sku": "MUG", "quantity": 1}], catalog)
except ValueError as exc:
    assert "mixed" in str(exc)
else:
    raise AssertionError("Expected mixed currency error")

product = Product("PEN", "Pen", Money(125, "USD"))
assert price_cents(product) == 125
assert currency(product) == "USD"

legacy = {"sku": "PAD", "name": "Pad", "price_cents": "300", "currency": "USD"}
assert price_cents(legacy) == 300
assert currency(legacy) == "USD"

new_dict = {"sku": "PEN", "name": "Pen", "price": {"amount_cents": "125", "currency": "USD"}}
assert price_cents(new_dict) == 125
assert currency(new_dict) == "USD"
PY
```

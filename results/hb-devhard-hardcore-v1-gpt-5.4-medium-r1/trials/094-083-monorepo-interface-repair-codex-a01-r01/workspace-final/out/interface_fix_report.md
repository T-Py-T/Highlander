Root cause: `orders` still assumed every product exposed a top-level integer `price_cents` and optional top-level `currency`. After `catalog` moved to `Product.price: Money(amount_cents, currency)`, `orders.adapter` no longer understood the new object shape, which broke both order pricing and report aggregation when fed catalog products.

Changed files:
- `packages/orders/orders/adapter.py`
  - Updated `price_cents(product)` to support both legacy dictionaries with `price_cents` and new products or dictionaries that carry `price` as a `Money`-like object.
  - Updated `currency(product)` to read currency from either the legacy top-level field or the nested `price.currency` field.
  - Added a small shared helper for reading `Money` values from either dict-backed or attribute-backed price objects.

Verification command:
- Attempted requested command: `python -m pytest tests`
  - Environment issue: `python` was unavailable, and `python3 -m pytest tests` failed because `pytest` is not installed in this runtime.
- Behavioral verification actually run:
  - `python3 - <<'PY'`
  - with `sys.path` extended to `packages/catalog`, `packages/orders`, and `packages/reports`
  - assertions covered:
    - new `Product(..., Money(...))` contract
    - legacy product dicts with `price_cents`
    - dicts carrying nested `price.amount_cents` and `price.currency`
    - order totals
    - report revenue grouped by currency
    - mixed-currency order rejection with a clear `ValueError`

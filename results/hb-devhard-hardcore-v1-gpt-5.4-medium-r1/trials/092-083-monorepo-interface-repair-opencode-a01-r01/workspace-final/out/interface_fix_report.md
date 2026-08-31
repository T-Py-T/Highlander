Root cause: `packages/orders/orders/adapter.py` still assumed the legacy catalog contract (`price_cents` and top-level `currency`). After `catalog` moved product pricing to `Product.price: Money(amount_cents, currency)`, `orders` could no longer read prices or currencies from catalog `Product` objects, which broke downstream `reports` integration.

Changed files:
- `packages/orders/orders/adapter.py`: updated `price_cents()` and `currency()` to read the new `Money` object shape from catalog `Product` instances, while preserving support for legacy product dictionaries containing `price_cents` and `currency`.

Verification command:
- Intended command: `python -m pytest tests`
- Environment note: `python` and `pytest` were unavailable in this runtime, so verification was performed with `python3` using direct assertions that covered the same catalog/orders/reports scenarios, plus `python3 -m compileall packages`.

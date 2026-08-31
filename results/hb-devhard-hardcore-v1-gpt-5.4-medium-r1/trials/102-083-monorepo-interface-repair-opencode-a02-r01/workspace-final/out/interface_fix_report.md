Root cause: `packages/orders/orders/adapter.py` still assumed the legacy catalog interface and read `price_cents` and top-level `currency` directly from product records. After `catalog` migrated to `Product(price=Money(amount_cents, currency))`, `orders` no longer extracted price and currency from the nested `Money` object, which broke both order pricing and report aggregation.

Changed files:
- `packages/orders/orders/adapter.py`: added compatibility logic to read price and currency from the new `price` / `Money` shape first, while preserving support for legacy product dictionaries that still expose `price_cents`.

Verification:
- Requested command attempted in this environment: `python -m pytest tests` from `shopmono` failed because `python` is not installed here.
- Follow-up attempt: `python3 -m pytest tests` failed because `pytest` is not installed here.
- Manual verification executed from `shopmono` with `python3` imports and assertions covering:
  - pricing orders with `catalog.Product(..., price=Money(...))`
  - report aggregation by currency
  - rejection of mixed-currency orders
  - legacy product dictionaries with `price_cents`

Verification command:
- `python -m pytest tests`

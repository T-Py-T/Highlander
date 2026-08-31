# Interface Fix Report

## Root cause
The `catalog` package migrated product pricing from the legacy flat `price_cents`/`currency` shape to `Product.price`, a `Money(amount_cents, currency)` object. The `orders` package still assumed products exposed `price_cents` and top-level `currency`, so cross-package calls failed for the new catalog model. That stale adapter logic also risked breaking reporting because `reports` depends on `orders.service.price_order`.

## Changed files
- `/workspace/in/shopmono/packages/orders/orders/adapter.py`
  - Added shared price extraction logic that supports:
    - new product objects with `price: Money`
    - legacy product dicts with `price_cents`
    - nested dict price payloads with `amount_cents` and `currency`
  - Updated `price_cents()` and `currency()` to read from the new `Money` model while preserving backward compatibility.
- `/workspace/in/shopmono/packages/orders/orders/service.py`
  - Kept mixed-currency validation in place.
  - Improved the error message to clearly identify the conflicting currencies in one order.

## Verification command
From `/workspace/in/shopmono`:

```bash
uv run --with pytest python -m pytest tests
```

## Verification result
The verification command completed successfully with `5 passed`.

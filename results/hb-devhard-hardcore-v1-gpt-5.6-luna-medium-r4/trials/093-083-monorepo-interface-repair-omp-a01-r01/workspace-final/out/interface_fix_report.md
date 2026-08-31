# Interface Fix Report

## Root cause

`catalog.Product` now stores its price in a `Money` object (`product.price.amount_cents` and `product.price.currency`). The `orders` adapter still read the removed `product.price_cents` and `product.currency` attributes. As a result, order pricing failed for current `Product` instances, and currency lookup could incorrectly fall back to USD. The reports package delegates pricing to `orders`, so it inherited the same breakage.

## Changed files

- `in/shopmono/packages/orders/orders/adapter.py`
  - Read `amount_cents` and `currency` from the current nested Money price.
  - Retain support for legacy dictionaries containing `price_cents` and optional top-level `currency`.
  - Also support dictionary representations with nested `price.amount_cents` and `price.currency`.
- `out/interface_fix_report.md`
  - Added this root-cause, change, and verification record.

`catalog` was not changed; the `Money` model remains the source-of-truth price representation. `orders.service.price_order` still rejects mixed currencies with `ValueError("mixed currencies are not supported")`.

## Verification

Requested command:

```text
python -m pytest tests
```

The supplied absolute macOS path is not mounted in this environment. From the available checkout at `/workspace/in/shopmono`, `python` is unavailable and `python3 -m pytest tests` cannot run because pytest is not installed.

A direct Python smoke check was run from `/workspace/in/shopmono` with the package paths configured. It verified:

- current `Product`/`Money` order totals;
- report aggregation by USD and EUR;
- legacy `price_cents` dictionaries;
- nested dictionary Money representations; and
- rejection of a mixed-currency order with an error containing `mixed`.

Command used:

```text
PYTHONPATH=packages/catalog:packages/orders:packages/reports python3 -c '...compatibility and mixed-currency assertions...'
```

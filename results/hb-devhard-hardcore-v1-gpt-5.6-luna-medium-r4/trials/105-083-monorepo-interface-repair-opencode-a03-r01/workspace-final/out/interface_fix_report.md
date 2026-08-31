# Interface Fix Report

## Root Cause

`orders.adapter` still read the removed legacy attributes `product.price_cents` and
`product.currency`. New catalog `Product` instances expose a `Money` object at
`product.price`, with the amount and currency nested inside it. This caused
orders to fail before reports could aggregate their normalized totals.

## Changed Files

- `packages/orders/orders/adapter.py`
  - Reads `Money.amount_cents` and `Money.currency` for new catalog products.
  - Retains support for legacy dictionaries containing `price_cents` and an
    optional top-level `currency`.
  - Leaves the order service's mixed-currency validation unchanged, so an order
    containing different currencies still raises `ValueError("mixed currencies
    are not supported")`.

## Verification

- Requested command: `python -m pytest tests`
  - Could not run because this environment has no `python` executable.
- `python3 -m compileall -q packages` passed.
- A dependency-free `python3` integration check passed for new `Money`
  products, legacy dictionaries, report aggregation, and mixed-currency
  rejection.

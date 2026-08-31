# Interface Fix Report

## Root cause

`orders.adapter` still read the removed `product.price_cents` attribute for catalog `Product` objects. It also read `product.currency`, but currency now belongs to the nested `Money` value at `product.price.currency`. As a result, new catalog products failed during pricing and could incorrectly default to USD during currency checks.

## Changed files

- `packages/orders/orders/adapter.py` — read `amount_cents` and `currency` from the nested `Money` object for new catalog products, while retaining `price_cents` and the optional `currency` field for legacy product dictionaries.

The `orders.service` currency comparison remains active, so differing currencies in one order raise `ValueError("mixed currencies are not supported")`. The `catalog` `Money` model was not changed.

## Verification command

- `python -m pytest tests`

The requested command was attempted in the provided workspace, but its environment has no `python` executable and `/usr/bin/python3` has no `pytest` module. A direct Python smoke check was run with the repository package paths and covered new `Money` products, legacy dictionaries, reports grouped by currency, and mixed-currency rejection.

# Interface fix report

## Root cause
- `catalog` now exposes product prices as `product.price.amount_cents` and `product.price.currency`.
- `orders/orders/adapter.py` still read `price_cents` and `currency` from the top level.
- That broke `orders` for new `Product` objects and gave bad currency reads for cross-package flows used by `reports`.

## Changed files
- `packages/orders/orders/adapter.py`
  - Added one boundary helper that reads both new `Money` shapes and legacy `price_cents` dictionaries.
  - Kept legacy dict support.
- `packages/orders/orders/service.py`
  - Kept mixed-currency validation and made the error clearer by naming both currencies.

## Verification
- Attempted requested command: `python -m pytest tests`
  - This environment does not provide `python` or the `pytest` module.
- Functional verification run:
  - `PYTHONPATH='packages/catalog:packages/orders:packages/reports' python3 - <<'PY'`
  - The script exercised the catalog contract, legacy dict contract, order pricing, report summary, and mixed-currency failure path.
  - Result: `manual verification passed`

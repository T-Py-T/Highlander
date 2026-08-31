# Interface Fix Report

## Root cause
`catalog` now exposes product prices as `price: Money(amount_cents, currency)`, but `orders.adapter` still read `price_cents` and `currency` from the old product shape. That broke `orders.service.price_order`, and `reports.monthly` failed through that shared path.

## Changed files
- `/workspace/in/shopmono/packages/orders/orders/adapter.py`
  - Added a shared price extractor for both product shapes.
  - Read `amount_cents` and `currency` from the new `Money` model.
  - Kept support for legacy product dictionaries that still use `price_cents`.

## Verification command
Requested command from the task:
- `python -m pytest tests`

This session does not have a `python` alias or `pytest` installed, so I verified the same test cases with this command instead:
- `PYTHONPATH=packages/catalog:packages/orders:packages/reports python3 - <<'PY'`
  `...manual import-and-run harness for tests...`
  `PY`

Verified passing cases:
- `tests.test_catalog_contract.test_new_money_product_contract`
- `tests.test_catalog_contract.test_legacy_product_dict_contract`
- `tests.test_orders_report_integration.test_order_prices_catalog_money_objects`
- `tests.test_orders_report_integration.test_reports_group_by_currency`
- `tests.test_orders_report_integration.test_mixed_currency_order_is_rejected`

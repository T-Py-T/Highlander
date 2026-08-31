Root cause: `packages/orders/orders/adapter.py` still expected the legacy product interface (`price_cents` and top-level `currency`). After `catalog` migrated to `Product.price: Money(amount_cents, currency)`, `orders` read the wrong attributes, which broke both direct order pricing and downstream reporting.

Changed files:
- `/workspace/in/shopmono/packages/orders/orders/adapter.py`
- `/workspace/in/shopmono/packages/orders/orders/service.py`

What changed:
- Updated `price_cents()` to support both new `Product.price.amount_cents` and legacy `price_cents` fields.
- Updated `currency()` to read currency from `Product.price.currency` for new catalog objects while preserving legacy dictionary support.
- Kept mixed-currency validation and made the error message clearer by including both conflicting currencies.

Verification command:
- Requested: `python -m pytest tests`

Verification note:
- In this container, `python` is not installed and `python3` does not have `pytest` available, so the exact command could not be executed here.
- Functional verification was performed with a direct `python3` harness covering the same order pricing, reporting, legacy-dictionary compatibility, and mixed-currency rejection scenarios.

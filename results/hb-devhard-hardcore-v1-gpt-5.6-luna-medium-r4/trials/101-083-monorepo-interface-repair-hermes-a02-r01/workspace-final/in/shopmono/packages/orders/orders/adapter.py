from __future__ import annotations


_DEFAULT_CURRENCY = "USD"


def _money(product):
    """Return the catalog price object, or ``None`` for a legacy record."""
    if isinstance(product, dict):
        return product.get("price")
    return getattr(product, "price", None)


def price_cents(product) -> int:
    """Return a product price from either supported catalog shape.

    Catalog products expose ``price.amount_cents``; legacy import records use
    ``price_cents`` directly.  Keeping this conversion at the orders boundary
    lets callers use either representation without changing the new catalog
    model.
    """
    money = _money(product)
    if money is not None:
        return int(money.amount_cents)
    if isinstance(product, dict):
        return int(product["price_cents"])
    return int(product.price_cents)


def currency(product) -> str:
    money = _money(product)
    if money is not None:
        return money.currency
    if isinstance(product, dict):
        return product.get("currency", _DEFAULT_CURRENCY)
    return getattr(product, "currency", _DEFAULT_CURRENCY)

from __future__ import annotations


def price_cents(product) -> int:
    """Return a product price in cents for either catalog price shape."""
    if isinstance(product, dict):
        if "price_cents" in product:
            return int(product["price_cents"])
        price = product["price"]
    else:
        legacy_price = getattr(product, "price_cents", None)
        if legacy_price is not None:
            return int(legacy_price)
        price = product.price

    if isinstance(price, dict):
        return int(price["amount_cents"])
    return int(price.amount_cents)


def currency(product) -> str:
    if isinstance(product, dict):
        if "price_cents" in product:
            return product.get("currency", "USD")
        price = product["price"]
    else:
        price = getattr(product, "price", None)
        if price is None:
            return getattr(product, "currency", "USD")

    if isinstance(price, dict):
        return price["currency"]
    return price.currency



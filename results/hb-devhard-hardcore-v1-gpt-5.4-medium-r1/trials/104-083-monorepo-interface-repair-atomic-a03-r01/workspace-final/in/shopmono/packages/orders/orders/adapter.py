from __future__ import annotations


def _price_value(product):
    if isinstance(product, dict):
        if "price" in product:
            return product["price"]
        return None
    return getattr(product, "price", None)


def price_cents(product) -> int:
    """Return the product price in cents for new and legacy product shapes."""
    price = _price_value(product)
    if price is not None:
        if isinstance(price, dict):
            return int(price["amount_cents"])
        return int(price.amount_cents)

    if isinstance(product, dict):
        return int(product["price_cents"])
    return int(product.price_cents)


def currency(product) -> str:
    price = _price_value(product)
    if price is not None:
        if isinstance(price, dict):
            return str(price["currency"])
        return str(price.currency)

    if isinstance(product, dict):
        return str(product.get("currency", "USD"))
    return str(getattr(product, "currency", "USD"))

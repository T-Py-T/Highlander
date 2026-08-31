from __future__ import annotations


def _price_value(product):
    if isinstance(product, dict):
        if "price" in product:
            return product["price"]
        return int(product["price_cents"])
    if hasattr(product, "price"):
        return product.price
    return int(product.price_cents)


def price_cents(product) -> int:
    """Return the product price in cents for both new and legacy product shapes."""
    price = _price_value(product)
    if hasattr(price, "amount_cents"):
        return int(price.amount_cents)
    return int(price)


def currency(product) -> str:
    price = _price_value(product)
    if hasattr(price, "currency"):
        return price.currency
    if isinstance(product, dict):
        return product.get("currency", "USD")
    return getattr(product, "currency", "USD")

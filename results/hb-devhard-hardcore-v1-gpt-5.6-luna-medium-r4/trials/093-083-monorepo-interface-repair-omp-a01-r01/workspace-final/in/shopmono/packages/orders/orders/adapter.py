from __future__ import annotations


def price_cents(product) -> int:
    """Return a product price in cents for current and legacy catalog shapes."""
    if isinstance(product, dict):
        if "price_cents" in product:
            return int(product["price_cents"])
        price = product["price"]
    else:
        price = product.price

    if isinstance(price, dict):
        return int(price["amount_cents"])
    return int(price.amount_cents)


def currency(product) -> str:
    """Return the currency from a Money price or legacy product dictionary."""
    if isinstance(product, dict):
        if "currency" in product:
            return product["currency"]
        price = product.get("price")
    else:
        price = product.price

    if isinstance(price, dict):
        return price.get("currency", "USD")
    return getattr(price, "currency", "USD")

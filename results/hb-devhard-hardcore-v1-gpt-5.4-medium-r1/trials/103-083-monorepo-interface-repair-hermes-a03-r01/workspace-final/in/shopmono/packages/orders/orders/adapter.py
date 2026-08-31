from __future__ import annotations


def _price_value(product):
    if isinstance(product, dict):
        if "price" in product:
            return product["price"]
        if "price_cents" in product:
            return product["price_cents"]
        raise KeyError("product is missing price information")

    if hasattr(product, "price"):
        return product.price
    if hasattr(product, "price_cents"):
        return product.price_cents
    raise AttributeError("product is missing price information")


def price_cents(product) -> int:
    """Return the product price in cents for new and legacy product shapes."""
    price = _price_value(product)
    if hasattr(price, "amount_cents"):
        return int(price.amount_cents)
    if isinstance(price, dict) and "amount_cents" in price:
        return int(price["amount_cents"])
    return int(price)


def currency(product) -> str:
    price = _price_value(product)
    if hasattr(price, "currency"):
        return str(price.currency)
    if isinstance(price, dict) and "currency" in price:
        return str(price["currency"])
    if isinstance(product, dict):
        return str(product.get("currency", "USD"))
    return str(getattr(product, "currency", "USD"))

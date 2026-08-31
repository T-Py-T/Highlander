from __future__ import annotations


def price_cents(product) -> int:
    """Return the product price in cents for catalog products and legacy dicts."""
    if isinstance(product, dict):
        if "price" in product:
            price = product["price"]
            if isinstance(price, dict):
                return int(price["amount_cents"])
            return int(price.amount_cents)
        return int(product["price_cents"])
    return int(product.price.amount_cents)


def currency(product) -> str:
    if isinstance(product, dict):
        if "price" in product:
            price = product["price"]
            if isinstance(price, dict):
                return str(price["currency"])
            return str(price.currency)
        return str(product.get("currency", "USD"))
    return str(product.price.currency)

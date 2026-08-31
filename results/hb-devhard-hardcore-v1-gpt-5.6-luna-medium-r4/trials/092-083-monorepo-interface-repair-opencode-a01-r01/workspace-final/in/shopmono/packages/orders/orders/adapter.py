from __future__ import annotations


def price_cents(product) -> int:
    """Return the product price in cents.

    Accept both the current Product/Money shape and legacy dictionaries.
    """
    if isinstance(product, dict):
        if "price" in product:
            return int(product["price"].amount_cents)
        return int(product["price_cents"])
    return int(product.price.amount_cents)


def currency(product) -> str:
    if isinstance(product, dict):
        if "price" in product:
            return product["price"].currency
        return product.get("currency", "USD")
    return product.price.currency

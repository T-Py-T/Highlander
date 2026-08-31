from __future__ import annotations


def price_cents(product) -> int:
    """Return a product price from either supported catalog representation."""
    if isinstance(product, dict):
        return int(product["price_cents"])
    return int(product.price.amount_cents)


def currency(product) -> str:
    if isinstance(product, dict):
        return product.get("currency", "USD")
    return product.price.currency

from __future__ import annotations


def price_cents(product) -> int:
    """Return a product price in cents for both catalog interfaces."""
    if isinstance(product, dict):
        return int(product["price_cents"])
    return int(product.price.amount_cents)


def currency(product) -> str:
    """Return the currency from a legacy mapping or a Money-backed product."""
    if isinstance(product, dict):
        return product.get("currency", "USD")
    return product.price.currency

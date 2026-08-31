from __future__ import annotations


def price_cents(product) -> int:
    """Return the product price in cents for current and legacy product shapes."""
    if isinstance(product, dict):
        if "price" in product:
            return int(product["price"]["amount_cents"])
        return int(product["price_cents"])
    if hasattr(product, "price"):
        return int(product.price.amount_cents)
    return int(product.price_cents)


def currency(product) -> str:
    if isinstance(product, dict):
        if "price" in product:
            return product["price"]["currency"]
        return product.get("currency", "USD")
    if hasattr(product, "price"):
        return product.price.currency
    return getattr(product, "currency", "USD")

from __future__ import annotations


def price_cents(product) -> int:
    """Return cents from either the current or legacy catalog shape."""
    if isinstance(product, dict):
        if "price_cents" in product:
            return int(product["price_cents"])
        return int(product["price"].amount_cents)

    price = getattr(product, "price", None)
    if price is not None:
        return int(price.amount_cents)
    return int(product.price_cents)


def currency(product) -> str:
    if isinstance(product, dict):
        price = product.get("price")
        if price is not None:
            return price.currency
        return product.get("currency", "USD")

    price = getattr(product, "price", None)
    if price is not None:
        return price.currency
    return getattr(product, "currency", "USD")

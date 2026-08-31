from __future__ import annotations


def price_cents(product) -> int:
    """Return the product price in cents.

    Supports both the new catalog Money model and legacy product dictionaries.
    """
    if isinstance(product, dict):
        if "price_cents" in product:
            return int(product["price_cents"])

        price = product["price"]
        if isinstance(price, dict):
            return int(price["amount_cents"])
        return int(price.amount_cents)

    if hasattr(product, "price"):
        return int(product.price.amount_cents)

    if hasattr(product, "price_cents"):
        return int(product.price_cents)

    raise AttributeError("product does not expose a supported price field")


def currency(product) -> str:
    if isinstance(product, dict):
        if "currency" in product:
            return str(product["currency"])

        price = product.get("price")
        if isinstance(price, dict):
            return str(price["currency"])
        if price is not None:
            return str(price.currency)

        return "USD"

    if hasattr(product, "price"):
        return str(product.price.currency)

    if hasattr(product, "currency"):
        return str(product.currency)

    return "USD"

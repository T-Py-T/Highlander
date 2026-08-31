from __future__ import annotations


def price_cents(product) -> int:
    """Return a product's amount in cents at the orders boundary.

    Catalog products use ``product.price.amount_cents``.  Legacy import
    records may still provide a ``price_cents`` dictionary field, so both
    representations are adapted here rather than leaking either shape into
    order pricing.
    """
    if isinstance(product, dict):
        if "price_cents" in product:
            return int(product["price_cents"])
        return int(product["price"]["amount_cents"])

    price = getattr(product, "price", None)
    if price is not None:
        return int(price.amount_cents)
    return int(product.price_cents)


def currency(product) -> str:
    """Return the currency carried by either supported product shape."""
    if isinstance(product, dict):
        if "currency" in product:
            return product["currency"]
        price = product.get("price")
        if price is not None:
            return price["currency"] if isinstance(price, dict) else price.currency
        return "USD"

    price = getattr(product, "price", None)
    if price is not None:
        return price.currency
    return getattr(product, "currency", "USD")

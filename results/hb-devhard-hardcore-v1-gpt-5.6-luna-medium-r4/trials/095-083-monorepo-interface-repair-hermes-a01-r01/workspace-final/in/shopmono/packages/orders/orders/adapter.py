from __future__ import annotations


def price_cents(product) -> int:
    """Return a product's price in cents across catalog interfaces.

    Catalog products now expose a ``Money`` value as ``product.price``.  The
    dictionary branch remains compatible with legacy catalog records.
    """
    if isinstance(product, dict):
        return int(product["price_cents"])

    return int(product.price.amount_cents)


def currency(product) -> str:
    """Return the currency carried by a new or legacy catalog product."""
    if isinstance(product, dict):
        return product.get("currency", "USD")

    return product.price.currency

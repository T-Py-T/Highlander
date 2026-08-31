from __future__ import annotations


def _money_from_product(product):
    if isinstance(product, dict):
        if "price" in product:
            return product["price"]
        return None
    return getattr(product, "price", None)


def price_cents(product) -> int:
    """Return the product price in cents for both new and legacy shapes."""
    money = _money_from_product(product)
    if money is not None:
        if isinstance(money, dict):
            return int(money["amount_cents"])
        return int(money.amount_cents)
    if isinstance(product, dict):
        return int(product["price_cents"])
    return int(product.price_cents)


def currency(product) -> str:
    money = _money_from_product(product)
    if money is not None:
        if isinstance(money, dict):
            return str(money["currency"])
        return str(money.currency)
    if isinstance(product, dict):
        return str(product.get("currency", "USD"))
    return str(getattr(product, "currency", "USD"))

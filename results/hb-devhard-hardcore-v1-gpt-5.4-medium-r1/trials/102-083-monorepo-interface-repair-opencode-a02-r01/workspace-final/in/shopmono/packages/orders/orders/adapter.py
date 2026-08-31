from __future__ import annotations


def _price_money(product):
    if isinstance(product, dict):
        return product.get("price")
    return getattr(product, "price", None)


def price_cents(product) -> int:
    money = _price_money(product)
    if money is not None:
        if isinstance(money, dict):
            return int(money["amount_cents"])
        return int(money.amount_cents)

    if isinstance(product, dict):
        return int(product["price_cents"])
    return int(product.price_cents)


def currency(product) -> str:
    money = _price_money(product)
    if money is not None:
        if isinstance(money, dict):
            return str(money["currency"])
        return str(money.currency)

    if isinstance(product, dict):
        return str(product.get("currency", "USD"))
    return getattr(product, "currency", "USD")

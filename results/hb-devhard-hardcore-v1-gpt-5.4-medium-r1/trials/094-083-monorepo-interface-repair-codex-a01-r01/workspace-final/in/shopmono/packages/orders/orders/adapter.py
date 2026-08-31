from __future__ import annotations


def price_cents(product) -> int:
    if isinstance(product, dict):
        if "price_cents" in product:
            return int(product["price_cents"])
        if "price" in product:
            return int(_money_value(product["price"], "amount_cents"))
        raise KeyError("product is missing price data")
    if hasattr(product, "price"):
        return int(_money_value(product.price, "amount_cents"))
    return int(product.price_cents)


def currency(product) -> str:
    if isinstance(product, dict):
        if "currency" in product:
            return str(product["currency"])
        if "price" in product:
            return str(_money_value(product["price"], "currency"))
        return "USD"
    if hasattr(product, "price"):
        return str(_money_value(product.price, "currency"))
    return str(getattr(product, "currency", "USD"))


def _money_value(price, field: str):
    if isinstance(price, dict):
        return price[field]
    return getattr(price, field)

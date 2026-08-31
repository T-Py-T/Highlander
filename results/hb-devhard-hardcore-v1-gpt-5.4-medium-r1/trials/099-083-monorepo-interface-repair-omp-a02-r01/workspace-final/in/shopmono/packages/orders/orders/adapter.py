from __future__ import annotations


def _price_data(product) -> tuple[int, str]:
    if isinstance(product, dict):
        price = product.get("price")
        if isinstance(price, dict):
            return int(price["amount_cents"]), str(price["currency"])
        if price is not None:
            return int(price.amount_cents), str(price.currency)
        return int(product["price_cents"]), str(product.get("currency", "USD"))

    price = getattr(product, "price", None)
    if price is not None:
        return int(price.amount_cents), str(price.currency)

    return int(product.price_cents), str(getattr(product, "currency", "USD"))


def price_cents(product) -> int:
    return _price_data(product)[0]


def currency(product) -> str:
    return _price_data(product)[1]

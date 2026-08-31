from __future__ import annotations


def _money_from_product(product):
    if isinstance(product, dict):
        price = product.get("price")
        if price is not None:
            return price
        if "price_cents" in product:
            return {"amount_cents": product["price_cents"], "currency": product.get("currency", "USD")}
        raise KeyError("product is missing both 'price' and 'price_cents'")

    price = getattr(product, "price", None)
    if price is not None:
        return price

    if hasattr(product, "price_cents"):
        return {
            "amount_cents": getattr(product, "price_cents"),
            "currency": getattr(product, "currency", "USD"),
        }

    raise AttributeError("product is missing both 'price' and 'price_cents'")


def price_cents(product) -> int:
    """Return the product price in cents for either catalog contract."""
    money = _money_from_product(product)
    if isinstance(money, dict):
        return int(money["amount_cents"])
    return int(money.amount_cents)


def currency(product) -> str:
    money = _money_from_product(product)
    if isinstance(money, dict):
        return str(money.get("currency", "USD"))
    return str(getattr(money, "currency", "USD"))

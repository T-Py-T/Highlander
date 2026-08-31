from __future__ import annotations


def _money_parts(product) -> tuple[int, str]:
    if isinstance(product, dict):
        if "price" in product:
            money = product["price"]
            if isinstance(money, dict):
                return int(money["amount_cents"]), str(money["currency"])
            return int(money.amount_cents), str(money.currency)
        return int(product["price_cents"]), str(product.get("currency", "USD"))

    money = getattr(product, "price", None)
    if money is not None:
        return int(money.amount_cents), str(money.currency)

    return int(product.price_cents), str(getattr(product, "currency", "USD"))


def price_cents(product) -> int:
    """Return the product price in cents for new and legacy product shapes."""
    amount_cents, _ = _money_parts(product)
    return amount_cents


def currency(product) -> str:
    _, code = _money_parts(product)
    return code

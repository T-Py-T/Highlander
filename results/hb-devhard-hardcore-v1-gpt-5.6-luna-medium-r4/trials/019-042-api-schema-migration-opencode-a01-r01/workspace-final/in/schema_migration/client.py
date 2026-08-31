"""Conversion helpers for the legacy and public order APIs."""

import copy
import json
import sys
from pathlib import Path


_PII_KEYS = {
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "phone_number",
    "passport_number",
}


class ConversionError(ValueError):
    def __init__(self, path, message):
        self.path = path
        super().__init__(message)


def _required(mapping, key, path):
    if not isinstance(mapping, dict) or key not in mapping:
        raise ConversionError(path, "missing required field")
    return mapping[key]


def _integer(value, path):
    if isinstance(value, bool):
        raise ConversionError(path, "must be an integer")
    try:
        converted = int(value)
    except (TypeError, ValueError):
        raise ConversionError(path, "must be an integer") from None
    if isinstance(value, float) and value != converted:
        raise ConversionError(path, "must be an integer")
    if isinstance(value, str) and str(converted) != value.strip():
        raise ConversionError(path, "must be an integer")
    return converted


def _shipping_method(payload):
    method = payload.get("shipping_method", payload.get("shipping"))
    return method if method not in (None, "") else "standard"


def _legacy_conversion(payload):
    if not isinstance(payload, dict):
        raise ConversionError("payload", "must be an object")

    order_id = payload.get("id", payload.get("order_ref"))
    if order_id is None:
        raise ConversionError("orderId", "missing id or order_ref")

    customer = payload.get("customer")
    buyer_id = payload.get("customer_id")
    buyer_name = payload.get("customer_name")
    if isinstance(customer, dict):
        buyer_id = customer.get("id", buyer_id)
        buyer_name = customer.get("name", buyer_name)
    if buyer_id is None:
        raise ConversionError("customer_id", "missing customer id")
    if buyer_name is None:
        raise ConversionError("customer_name", "missing customer name")

    items = payload.get("items", payload.get("lines"))
    if not isinstance(items, list):
        raise ConversionError("items", "missing or must be an array")
    line_items = []
    for index, item in enumerate(items):
        item_path = f"items[{index}]"
        if not isinstance(item, dict):
            raise ConversionError(item_path, "must be an object")
        sku = _required(item, "sku", f"{item_path}.sku")
        quantity = _integer(_required(item, "qty", f"{item_path}.qty"), f"{item_path}.qty")
        price = item.get("price_cents", item.get("unit_price_cents"))
        if price is None:
            raise ConversionError(f"{item_path}.price_cents", "missing price_cents or unit_price_cents")
        line_items.append({
            "sku": sku,
            "quantity": quantity,
            "unitPriceCents": _integer(price, f"{item_path}.price_cents"),
        })

    address = payload.get("ship_to", payload.get("shipTo"))
    if not isinstance(address, dict):
        raise ConversionError("ship_to", "missing or must be an object")
    country = _required(address, "country", "ship_to.country")
    postal = address.get("postal", address.get("postalCode", address.get("postal_code")))
    if postal is None:
        raise ConversionError("ship_to.postal", "missing postal, postalCode, or postal_code")

    known = {
        "id", "order_ref", "customer_id", "customer_name", "customer",
        "items", "lines", "ship_to", "shipTo", "shipping_method", "shipping",
    }
    unknown = {}
    dropped = 0
    for key, value in payload.items():
        if key in known:
            continue
        if str(key).lower() in _PII_KEYS:
            dropped += 1
        else:
            unknown[key] = copy.deepcopy(value)

    metadata = {"source": "legacy-v1"}
    if unknown:
        metadata["unknownFields"] = unknown
    result = {
        "orderId": order_id,
        "buyer": {"id": buyer_id, "displayName": buyer_name},
        "lineItems": line_items,
        "shipping": {
            "method": _shipping_method(payload),
            "address": {"country": country, "postalCode": postal},
        },
        "metadata": metadata,
    }
    return result, dropped, len(unknown)


def _v2_conversion(payload):
    if not isinstance(payload, dict):
        raise ConversionError("payload", "must be an object")
    for key in ("orderId", "buyer", "lineItems", "shipping", "metadata"):
        _required(payload, key, key)
    if not isinstance(payload["buyer"], dict):
        raise ConversionError("buyer", "must be an object")
    for key in ("id", "displayName"):
        _required(payload["buyer"], key, f"buyer.{key}")
    if not isinstance(payload["lineItems"], list):
        raise ConversionError("lineItems", "must be an array")
    if not isinstance(payload["shipping"], dict):
        raise ConversionError("shipping", "must be an object")
    _required(payload["shipping"], "address", "shipping.address")
    if not isinstance(payload["metadata"], dict):
        raise ConversionError("metadata", "must be an object")
    result = copy.deepcopy(payload)
    if result["shipping"].get("method") in (None, ""):
        result["shipping"]["method"] = "standard"
    return result, 0, len(result["metadata"].get("unknownFields", {}))


def convert_order(payload):
    """Convert a legacy order or return an already-v2 order unchanged."""
    if isinstance(payload, dict) and "orderId" in payload:
        return _v2_conversion(payload)[0]
    return _legacy_conversion(payload)[0]


def convert_many(payloads):
    converted, errors, warnings = [], [], []
    pii_dropped_count = unknown_fields_count = 0
    for index, payload in enumerate(payloads):
        try:
            result, dropped, unknown_count = (
                _v2_conversion(payload) if isinstance(payload, dict) and "orderId" in payload
                else _legacy_conversion(payload)
            )
            converted.append(result)
            pii_dropped_count += dropped
            unknown_fields_count += unknown_count
        except ConversionError as exc:
            errors.append({"index": index, "path": exc.path, "error": str(exc)})
        except (KeyError, TypeError, ValueError) as exc:
            errors.append({"index": index, "path": "payload", "error": str(exc)})

    audit = {
        "converted_count": len(converted),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "pii_dropped_count": pii_dropped_count,
        "unknown_fields_count": unknown_fields_count,
    }
    Path(__file__).with_name("conversion_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return (converted, errors, warnings) if warnings else (converted, errors)


def summarize_order(v2_payload):
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        raise SystemExit("usage: python -m client input.jsonl output.json")
    payloads = []
    with Path(argv[0]).open() as source:
        for line_number, line in enumerate(source):
            if not line.strip():
                continue
            try:
                payloads.append(json.loads(line))
            except json.JSONDecodeError as exc:
                payloads.append({"__invalid_json__": True, "line": line_number + 1})
    converted, _errors = convert_many(payloads)[:2]
    Path(argv[1]).write_text(json.dumps(converted, indent=2) + "\n")


if __name__ == "__main__":
    main()

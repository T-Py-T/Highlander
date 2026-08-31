"""Legacy order payload migration utilities."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


_PII_KEYS = {
    "ssn", "credit_card", "card_number", "cvv", "phone_number", "passport_number",
}
_LEGACY_FIELDS = {
    "id", "order_ref", "customer_id", "customer_name", "customer",
    "items", "lines", "ship_to", "shipTo", "shipping_method", "shipping",
}


class ConversionError(ValueError):
    """Raised when a payload cannot satisfy the target order shape."""

    def __init__(self, message, path="payload"):
        super().__init__(message)
        self.path = path


def _require_mapping(value, path):
    if not isinstance(value, dict):
        raise ConversionError(f"{path} must be an object", path)
    return value



def _required_string(value, path):
    if not isinstance(value, str) or not value:
        raise ConversionError(f"missing or invalid {path}", path)
    return value


def _integer(value, path):
    if isinstance(value, bool):
        raise ConversionError(f"{path} must be an integer", path)
    try:
        converted = int(value)
    except (TypeError, ValueError):
        raise ConversionError(f"{path} must be an integer", path) from None
    if isinstance(value, float) and not value.is_integer():
        raise ConversionError(f"{path} must be an integer", path)
    if isinstance(value, str) and str(converted) != value.strip():
        raise ConversionError(f"{path} must be an integer", path)
    return converted


def _shipping_method(value):
    return value.strip() if isinstance(value, str) and value.strip() else "standard"


def _drop_pii_and_count(value):
    if not isinstance(value, dict):
        return copy.deepcopy(value), 0
    result = {}
    dropped = 0
    for key, item in value.items():
        if str(key).lower() in _PII_KEYS:
            dropped += 1
            continue
        cleaned, nested_dropped = _drop_pii_and_count(item)
        result[key] = cleaned
        dropped += nested_dropped
    return result, dropped


def _legacy_unknown_fields(payload):
    unknown = {key: value for key, value in payload.items()
               if key not in _LEGACY_FIELDS}
    return _drop_pii_and_count(unknown)


def _convert_v2(payload):
    result = copy.deepcopy(payload)
    if not isinstance(result, dict):
        raise ConversionError("payload must be an object", "payload")
    for key in ("orderId", "buyer", "lineItems", "shipping", "metadata"):
        if key not in result:
            raise ConversionError(f"missing {key}", key)
    _required_string(result["orderId"], "orderId")
    buyer = _require_mapping(result["buyer"], "buyer")
    _required_string(buyer.get("id"), "buyer.id")
    _required_string(buyer.get("displayName"), "buyer.displayName")
    if not isinstance(result["lineItems"], list):
        raise ConversionError("lineItems must be an array", "lineItems")
    shipping = _require_mapping(result["shipping"], "shipping")
    shipping["method"] = _shipping_method(shipping.get("method"))
    _require_mapping(shipping.get("address"), "shipping.address")
    metadata = _require_mapping(result["metadata"], "metadata")
    unknown = metadata.get("unknownFields")
    return result, 0, len(unknown) if isinstance(unknown, dict) else 0


def _convert_legacy(payload):
    if not isinstance(payload, dict):
        raise ConversionError("payload must be an object")
    order_id = payload.get("id", payload.get("order_ref"))
    _required_string(order_id, "orderId")
    customer = payload.get("customer")
    if customer is not None:
        customer = _require_mapping(customer, "customer")
        buyer_id, display_name = customer.get("id"), customer.get("name")
    else:
        buyer_id, display_name = payload.get("customer_id"), payload.get("customer_name")
    _required_string(buyer_id, "customer_id")
    _required_string(display_name, "customer_name")

    raw_items = payload.get("items", payload.get("lines"))
    if not isinstance(raw_items, list):
        raise ConversionError("missing items", "items")
    line_items = []
    for index, item in enumerate(raw_items):
        item = _require_mapping(item, f"items[{index}]")
        quantity = _integer(item.get("qty"), f"items[{index}].qty")
        price = item.get("price_cents", item.get("unit_price_cents"))
        price = _integer(price, f"items[{index}].price_cents")
        line_items.append({"sku": item.get("sku"), "quantity": quantity, "unitPriceCents": price})

    address = payload.get("ship_to", payload.get("shipTo"))
    address = _require_mapping(address, "ship_to")
    postal = address.get("postal", address.get("postalCode", address.get("postal_code")))
    _required_string(postal, "ship_to.postal")
    shipping = {
        "method": _shipping_method(payload.get("shipping_method", payload.get("shipping"))),
        "address": {"country": address.get("country"), "postalCode": postal},
    }
    unknown, pii_dropped = _legacy_unknown_fields(payload)
    metadata = {"source": "legacy-v1"}
    if unknown:
        metadata["unknownFields"] = unknown
    return {
        "orderId": order_id,
        "buyer": {"id": buyer_id, "displayName": display_name},
        "lineItems": line_items,
        "shipping": shipping,
        "metadata": metadata,
    }, pii_dropped, len(unknown)


def convert_order(payload):
    """Convert a legacy order or normalize an already-v2 order."""
    if isinstance(payload, dict) and (
        "orderId" in payload or "lineItems" in payload or "buyer" in payload
    ):
        return _convert_v2(payload)[0]
    return _convert_legacy(payload)[0]


def convert_many(payloads):
    """Convert all records, collecting per-record errors and writing an audit."""
    converted, errors = [], []
    pii_dropped_count = unknown_fields_count = 0
    for index, payload in enumerate(payloads):
        try:
            if isinstance(payload, dict) and (
                "orderId" in payload or "lineItems" in payload or "buyer" in payload
            ):
                result, dropped, unknown_count = _convert_v2(payload)
            else:
                result, dropped, unknown_count = _convert_legacy(payload)
            converted.append(result)
            pii_dropped_count += dropped
            unknown_fields_count += unknown_count
        except (ConversionError, KeyError, TypeError, ValueError) as exc:
            path = getattr(exc, "path", "payload")
            errors.append({"index": index, "path": path, "error": str(exc)})
    audit = {
        "converted_count": len(converted),
        "error_count": len(errors),
        "warning_count": 0,
        "pii_dropped_count": pii_dropped_count,
        "unknown_fields_count": unknown_fields_count,
    }
    Path(__file__).with_name("conversion_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    return converted, errors


def summarize_order(v2_payload):
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        raise SystemExit("usage: python -m client input.jsonl output.json")
    input_path, output_path = map(Path, argv)
    with input_path.open(encoding="utf-8") as stream:
        payloads = [json.loads(line) for line in stream if line.strip()]
    converted, errors = convert_many(payloads)
    output_path.write_text(json.dumps(converted, indent=2) + "\n", encoding="utf-8")
    if errors:
        raise SystemExit(json.dumps(errors))


if __name__ == "__main__":
    main()

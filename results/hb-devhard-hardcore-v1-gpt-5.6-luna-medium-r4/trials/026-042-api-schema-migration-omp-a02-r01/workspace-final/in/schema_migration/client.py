"""Legacy order payload migration to the public v2 API shape."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any


_AUDIT_PATH = Path(__file__).with_name("conversion_audit.json")
_PII_KEYS = {
    "ssn",
    "creditcard",
    "cardnumber",
    "cvv",
    "phonenumber",
    "passportnumber",
}
_LEGACY_KEYS = {
    "id",
    "order_ref",
    "customer_id",
    "customer_name",
    "customer",
    "items",
    "lines",
    "ship_to",
    "shipTo",
    "shipping_method",
    "shipping",
}


class ConversionError(ValueError):
    """A payload error with a useful field path."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        super().__init__(f"{path}: {message}")


def _is_pii_key(key: str) -> bool:
    normalized = "".join(ch for ch in key.lower() if ch.isalnum())
    return normalized in _PII_KEYS


def _required(payload: dict[str, Any], key: str, path: str | None = None) -> Any:
    if key not in payload or payload[key] is None or payload[key] == "":
        raise ConversionError(path or key, f"missing required field {key}")
    return payload[key]


def _integer(value: Any, path: str) -> int:
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


def _legacy_item(item: Any, path: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ConversionError(path, "must be an object")
    sku = _required(item, "sku", f"{path}.sku")
    qty_key = "qty"
    price_key = "price_cents" if "price_cents" in item else "unit_price_cents"
    quantity = _integer(_required(item, qty_key, f"{path}.qty"), f"{path}.qty")
    unit_price = _integer(_required(item, price_key, f"{path}.{price_key}"), f"{path}.{price_key}")
    return {"sku": sku, "quantity": quantity, "unitPriceCents": unit_price}


def _legacy_convert(payload: dict[str, Any]) -> tuple[dict[str, Any], int, int]:
    order_id = payload.get("id", payload.get("order_ref"))
    if order_id is None or order_id == "":
        raise ConversionError("id" if "order_ref" not in payload else "order_ref", "missing order identifier")

    customer = payload.get("customer")
    if customer is not None:
        if not isinstance(customer, dict):
            raise ConversionError("customer", "must be an object")
        buyer_id = _required(customer, "id", "customer.id")
        display_name = _required(customer, "name", "customer.name")
    else:
        buyer_id = _required(payload, "customer_id")
        display_name = _required(payload, "customer_name")

    item_key = "lines" if "lines" in payload else "items"
    items = _required(payload, item_key)
    if not isinstance(items, list):
        raise ConversionError(item_key, "must be an array")
    line_items = [_legacy_item(item, f"{item_key}[{index}]") for index, item in enumerate(items)]

    ship_key = "shipTo" if "shipTo" in payload else "ship_to"
    ship_to = _required(payload, ship_key)
    if not isinstance(ship_to, dict):
        raise ConversionError(ship_key, "must be an object")
    address: dict[str, Any] = {}
    if "country" in ship_to:
        address["country"] = ship_to["country"]
    postal = ship_to.get("postal")
    if postal is None:
        postal = ship_to.get("postalCode")
    if postal is None:
        postal = ship_to.get("postal_code")
    if postal is not None:
        address["postalCode"] = postal

    method = payload.get("shipping_method", payload.get("shipping"))
    if method is None or (isinstance(method, str) and not method.strip()):
        method = "standard"

    unknown: dict[str, Any] = {}
    pii_dropped = 0
    for key, value in payload.items():
        if key in _LEGACY_KEYS:
            continue
        if _is_pii_key(key):
            pii_dropped += 1
        else:
            unknown[key] = copy.deepcopy(value)

    metadata: dict[str, Any] = {"source": "legacy-v1"}
    if unknown:
        metadata["unknownFields"] = unknown
    result = {
        "orderId": order_id,
        "buyer": {"id": buyer_id, "displayName": display_name},
        "lineItems": line_items,
        "shipping": {"method": method, "address": address},
        "metadata": metadata,
    }
    return result, pii_dropped, len(unknown)


def _v2_convert(payload: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    for key in ("orderId", "buyer", "lineItems", "shipping", "metadata"):
        if key not in result:
            raise ConversionError(key, f"missing required v2 field {key}")
    if not isinstance(result["lineItems"], list):
        raise ConversionError("lineItems", "must be an array")
    if not isinstance(result["shipping"], dict):
        raise ConversionError("shipping", "must be an object")
    method = result["shipping"].get("method")
    if method is None or (isinstance(method, str) and not method.strip()):
        result["shipping"]["method"] = "standard"
    return result


def _convert_with_stats(payload: Any) -> tuple[dict[str, Any], int, int]:
    if not isinstance(payload, dict):
        raise ConversionError("payload", "must be an object")
    if "orderId" in payload:
        return _v2_convert(payload), 0, 0
    return _legacy_convert(payload)


def convert_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert a legacy v1/v1.1/v1.2 or public v2 order payload."""
    return _convert_with_stats(payload)[0]


def convert_many(payloads: Any):
    """Convert all payloads, collecting per-record errors and writing an audit."""
    converted: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    pii_dropped = 0
    unknown_fields = 0
    for index, payload in enumerate(payloads):
        try:
            result, dropped, unknown = _convert_with_stats(payload)
            converted.append(result)
            pii_dropped += dropped
            unknown_fields += unknown
        except (ConversionError, TypeError, KeyError, ValueError) as exc:
            path = getattr(exc, "path", "payload")
            errors.append({"index": index, "path": path, "error": str(exc)})
    audit = {
        "converted_count": len(converted),
        "error_count": len(errors),
        "warning_count": 0,
        "pii_dropped_count": pii_dropped,
        "unknown_fields_count": unknown_fields,
    }
    _AUDIT_PATH.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return converted, errors


def summarize_order(v2_payload: dict[str, Any]) -> str:
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        raise SystemExit("usage: python -m client input.jsonl output.json")
    input_path, output_path = map(Path, args)
    payloads = []
    for line_number, line in enumerate(input_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payloads.append(json.loads(line))
        except json.JSONDecodeError as exc:
            payloads.append({"_invalid_json": line_number, "_error": str(exc)})
    converted, _errors = convert_many(payloads)
    Path(output_path).write_text(json.dumps(converted, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

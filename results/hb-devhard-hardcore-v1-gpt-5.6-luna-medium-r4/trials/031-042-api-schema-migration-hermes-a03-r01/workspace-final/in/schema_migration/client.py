"""Helpers for migrating legacy order payloads to the public v2 shape."""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_PII_KEYS = {
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "phone_number",
    "passport_number",
}


class ConversionError(ValueError):
    """A validation error carrying the useful payload path."""

    def __init__(self, path: str, message: str):
        self.path = path
        super().__init__(message)


def _is_pii(key: Any) -> bool:
    normalized = re.sub(r"[-\s]", "_", str(key).lower())
    return normalized in _PII_KEYS


def _required(payload: dict[str, Any], key: str, path: str | None = None) -> Any:
    if key not in payload or payload[key] is None:
        raise ConversionError(path or key, f"missing required field: {path or key}")
    return payload[key]


def _integer(value: Any, path: str) -> int:
    if isinstance(value, bool):
        raise ConversionError(path, "must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()):
        return int(value.strip())
    raise ConversionError(path, "must be an integer")


def _clean_unknown(value: Any) -> tuple[Any, int]:
    """Copy an unknown value while removing sensitive keys at any nesting level."""
    if isinstance(value, dict):
        cleaned = {}
        dropped = 0
        for key, child in value.items():
            if _is_pii(key):
                dropped += 1
            else:
                clean_child, child_dropped = _clean_unknown(child)
                cleaned[key] = clean_child
                dropped += child_dropped
        return cleaned, dropped
    if isinstance(value, list):
        cleaned = []
        dropped = 0
        for child in value:
            clean_child, child_dropped = _clean_unknown(child)
            cleaned.append(clean_child)
            dropped += child_dropped
        return cleaned, dropped
    return copy.deepcopy(value), 0


def _legacy_unknowns(payload: dict[str, Any]) -> tuple[dict[str, Any], int, int]:
    """Return top-level legacy extras, dropped PII count, and unknown count."""
    mapped = {
        "id", "order_ref", "customer_id", "customer_name", "customer",
        "items", "lines", "ship_to", "shipTo", "shipping_method", "shipping",
    }
    unknown: dict[str, Any] = {}
    pii_dropped = 0
    for key, value in payload.items():
        if key in mapped:
            continue
        if _is_pii(key):
            pii_dropped += 1
        else:
            clean_value, nested_dropped = _clean_unknown(value)
            unknown[key] = clean_value
            pii_dropped += nested_dropped
    return unknown, pii_dropped, len(unknown)


def _convert_legacy(payload: dict[str, Any]) -> dict[str, Any]:
    order_id = payload.get("id", payload.get("order_ref"))
    if order_id is None:
        raise ConversionError("id", "missing required field: id or order_ref")

    customer = payload.get("customer")
    if customer is not None:
        if not isinstance(customer, dict):
            raise ConversionError("customer", "must be an object")
        buyer_id = _required(customer, "id", "customer.id")
        display_name = _required(customer, "name", "customer.name")
    else:
        buyer_id = _required(payload, "customer_id")
        display_name = _required(payload, "customer_name")

    raw_items = payload.get("lines", payload.get("items"))
    if raw_items is None:
        raise ConversionError("items", "missing required field: items or lines")
    if not isinstance(raw_items, list):
        raise ConversionError("items", "must be an array")

    line_items = []
    for index, item in enumerate(raw_items):
        path = f"items[{index}]"
        if not isinstance(item, dict):
            raise ConversionError(path, "must be an object")
        sku = _required(item, "sku", f"{path}.sku")
        qty_key = "qty"
        price_key = "price_cents" if "price_cents" in item else "unit_price_cents"
        quantity = _integer(_required(item, qty_key, f"{path}.qty"), f"{path}.qty")
        unit_price = _integer(_required(item, price_key, f"{path}.{price_key}"), f"{path}.{price_key}")
        line_items.append({"sku": sku, "quantity": quantity, "unitPriceCents": unit_price})

    address = payload.get("shipTo", payload.get("ship_to"))
    if address is None:
        raise ConversionError("ship_to", "missing required field: ship_to or shipTo")
    if not isinstance(address, dict):
        raise ConversionError("ship_to", "must be an object")
    country = _required(address, "country", "ship_to.country")
    postal = address.get("postal", address.get("postalCode", address.get("postal_code")))
    if postal is None:
        raise ConversionError("ship_to.postal", "missing required postal field")

    method = payload.get("shipping_method", payload.get("shipping"))
    if method is None or (isinstance(method, str) and not method.strip()):
        method = "standard"
    unknown, _, _ = _legacy_unknowns(payload)
    metadata: dict[str, Any] = {"source": "legacy-v1"}
    if unknown:
        metadata["unknownFields"] = unknown
    return {
        "orderId": order_id,
        "buyer": {"id": buyer_id, "displayName": display_name},
        "lineItems": line_items,
        "shipping": {"method": method, "address": {"country": country, "postalCode": postal}},
        "metadata": metadata,
    }


def _convert_v2(payload: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    for key in ("orderId", "buyer", "lineItems", "shipping"):
        if key not in result:
            raise ConversionError(key, f"missing required field: {key}")
    if not isinstance(result["shipping"], dict):
        raise ConversionError("shipping", "must be an object")
    method = result["shipping"].get("method")
    if method is None or (isinstance(method, str) and not method.strip()):
        result["shipping"]["method"] = "standard"
    if "metadata" not in result or result["metadata"] is None:
        result["metadata"] = {"source": "public-v2"}
    elif not isinstance(result["metadata"], dict):
        raise ConversionError("metadata", "must be an object")
    return result


def convert_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert one legacy payload, or normalize an already-v2 payload."""
    if not isinstance(payload, dict):
        raise ConversionError("payload", "must be an object")
    if "orderId" in payload or "lineItems" in payload or "buyer" in payload:
        return _convert_v2(payload)
    return _convert_legacy(payload)


def _audit(converted_count: int, error_count: int, warning_count: int,
           pii_dropped_count: int, unknown_fields_count: int) -> None:
    data = {
        "converted_count": converted_count,
        "error_count": error_count,
        "warning_count": warning_count,
        "pii_dropped_count": pii_dropped_count,
        "unknown_fields_count": unknown_fields_count,
    }
    (_HERE / "conversion_audit.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def convert_many(payloads):
    converted, errors, warnings = [], [], []
    pii_dropped = unknown_count = 0
    for index, payload in enumerate(payloads):
        try:
            item = convert_order(payload)
            converted.append(item)
            if isinstance(payload, dict) and not any(k in payload for k in ("orderId", "lineItems", "buyer")):
                unknown, dropped, count = _legacy_unknowns(payload)
                pii_dropped += dropped
                unknown_count += count
        except (ConversionError, ValueError, TypeError, KeyError) as exc:
            path = getattr(exc, "path", "payload")
            errors.append({"index": index, "path": path, "error": str(exc)})
    _audit(len(converted), len(errors), len(warnings), pii_dropped, unknown_count)
    return converted, errors


def summarize_order(v2_payload):
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        raise SystemExit("usage: python -m client input.jsonl output.json")
    input_path, output_path = map(Path, argv)
    payloads = []
    with input_path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                payloads.append(json.loads(line))
            except json.JSONDecodeError as exc:
                payloads.append({"__invalid_json__": f"line {number}: {exc}"})
    converted, errors = convert_many(payloads)
    Path(output_path).write_text(json.dumps(converted, indent=2) + "\n", encoding="utf-8")
    if errors:
        # Keep the output contract as converted records while making failures visible on stderr.
        print(json.dumps({"errors": errors}, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

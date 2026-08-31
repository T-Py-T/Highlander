"""Utilities for migrating legacy order payloads to the public v2 shape."""

from __future__ import annotations

import copy
import json
import os
import sys
from typing import Any


PII_KEYS = {
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "phone_number",
    "passport_number",
}

_MISSING = object()


class ConversionError(ValueError):
    """A payload error with a useful source path."""

    def __init__(self, path: str, message: str):
        self.path = path
        super().__init__(message)


def _required(payload: dict[str, Any], key: str, path: str | None = None) -> Any:
    value = payload.get(key, _MISSING)
    if value is _MISSING or value is None:
        raise ConversionError(path or key, f"missing required field: {path or key}")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConversionError(path, f"{path} must be a non-empty string")
    return value


def _integer(value: Any, path: str) -> int:
    # bool is an int subclass, but is not a meaningful quantity or price.
    if isinstance(value, bool):
        raise ConversionError(path, f"{path} must be an integer")
    try:
        converted = int(value)
    except (TypeError, ValueError):
        raise ConversionError(path, f"{path} must be an integer") from None
    if isinstance(value, float) and value != converted:
        raise ConversionError(path, f"{path} must be an integer")
    if isinstance(value, str) and str(converted) != value.strip():
        raise ConversionError(path, f"{path} must be an integer")
    return converted


def _is_pii(key: str) -> bool:
    return key.lower() in PII_KEYS


def _copy_unknown_fields(payload: dict[str, Any], known: set[str]) -> tuple[dict[str, Any], int, int]:
    unknown: dict[str, Any] = {}
    dropped = 0
    for key, value in payload.items():
        if key in known:
            continue
        if _is_pii(str(key)):
            dropped += 1
        else:
            unknown[key] = copy.deepcopy(value)
    return unknown, dropped, len(unknown)


def _legacy_order(payload: dict[str, Any]) -> tuple[dict[str, Any], int, int]:
    if not isinstance(payload, dict):
        raise ConversionError("payload", "payload must be an object")

    if "order_ref" in payload:
        order_id = _string(_required(payload, "order_ref"), "order_ref")
    else:
        order_id = _string(_required(payload, "id"), "id")

    customer = payload.get("customer")
    if customer is not None:
        if not isinstance(customer, dict):
            raise ConversionError("customer", "customer must be an object")
        buyer_id = _string(_required(customer, "id", "customer.id"), "customer.id")
        buyer_name = _string(_required(customer, "name", "customer.name"), "customer.name")
    else:
        buyer_id = _string(_required(payload, "customer_id"), "customer_id")
        buyer_name = _string(_required(payload, "customer_name"), "customer_name")

    items_key = "lines" if "lines" in payload else "items"
    items = _required(payload, items_key, items_key)
    if not isinstance(items, list):
        raise ConversionError(items_key, f"{items_key} must be an array")
    line_items = []
    for index, item in enumerate(items):
        path = f"{items_key}[{index}]"
        if not isinstance(item, dict):
            raise ConversionError(path, f"{path} must be an object")
        sku = _string(_required(item, "sku", f"{path}.sku"), f"{path}.sku")
        quantity = _integer(_required(item, "qty", f"{path}.qty"), f"{path}.qty")
        price_key = "unit_price_cents" if "unit_price_cents" in item else "price_cents"
        price = _integer(_required(item, price_key, f"{path}.{price_key}"), f"{path}.{price_key}")
        line_items.append({"sku": sku, "quantity": quantity, "unitPriceCents": price})

    address = payload.get("shipTo") if "shipTo" in payload else payload.get("ship_to")
    address_key = "shipTo" if "shipTo" in payload else "ship_to"
    address = _required(payload, address_key, address_key)
    if not isinstance(address, dict):
        raise ConversionError(address_key, f"{address_key} must be an object")
    country = _required(address, "country", f"{address_key}.country")
    postal_key = "postal_code" if "postal_code" in address else ("postalCode" if "postalCode" in address else "postal")
    postal = _required(address, postal_key, f"{address_key}.{postal_key}")
    shipping_method = payload.get("shipping_method", payload.get("shipping"))
    if shipping_method is None or (isinstance(shipping_method, str) and not shipping_method.strip()):
        shipping_method = "standard"
    if not isinstance(shipping_method, str):
        raise ConversionError("shipping_method", "shipping method must be a string")

    known = {"id", "order_ref", "customer_id", "customer_name", "customer", "items", "lines",
             "ship_to", "shipTo", "shipping_method", "shipping"}
    unknown, dropped, unknown_count = _copy_unknown_fields(payload, known)
    metadata = {"source": "legacy-v1"}
    if unknown:
        metadata["unknownFields"] = unknown
    converted = {
        "orderId": order_id,
        "buyer": {"id": buyer_id, "displayName": buyer_name},
        "lineItems": line_items,
        "shipping": {"method": shipping_method,
                     "address": {"country": copy.deepcopy(country), "postalCode": copy.deepcopy(postal)}},
        "metadata": metadata,
    }
    return converted, dropped, unknown_count


def _v2_order(payload: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    for field in ("orderId", "buyer", "lineItems", "shipping", "metadata"):
        if field not in result:
            raise ConversionError(field, f"missing required field: {field}")
    if not isinstance(result["shipping"], dict):
        raise ConversionError("shipping", "shipping must be an object")
    method = result["shipping"].get("method")
    if method is None or (isinstance(method, str) and not method.strip()):
        result["shipping"]["method"] = "standard"
    return result


def convert_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert a legacy order, or return an idempotent copy of a v2 order."""
    if isinstance(payload, dict) and any(k in payload for k in ("orderId", "buyer", "lineItems")):
        return _v2_order(payload)
    return _legacy_order(payload)[0]


def convert_many(payloads):
    """Convert all records, collecting errors and writing a conversion audit."""
    converted, errors, warnings = [], [], []
    pii_dropped_count = unknown_fields_count = 0
    for index, payload in enumerate(payloads):
        try:
            if isinstance(payload, dict) and any(k in payload for k in ("orderId", "buyer", "lineItems")):
                item = _v2_order(payload)
            else:
                item, dropped, unknown_count = _legacy_order(payload)
                pii_dropped_count += dropped
                unknown_fields_count += unknown_count
            converted.append(item)
        except ConversionError as exc:
            errors.append({"index": index, "path": exc.path, "error": str(exc)})
        except Exception as exc:
            errors.append({"index": index, "path": "payload", "error": str(exc)})
    audit = {"converted_count": len(converted), "error_count": len(errors),
             "warning_count": len(warnings), "pii_dropped_count": pii_dropped_count,
             "unknown_fields_count": unknown_fields_count}
    audit_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conversion_audit.json")
    with open(audit_path, "w", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2, sort_keys=True)
        handle.write("\n")
    # Keep the original two-value calling convention when there are no warnings.
    # A caller that opts into warning-producing migrations can receive the third
    # value without changing the audit format.
    return (converted, errors, warnings) if warnings else (converted, errors)


def summarize_order(v2_payload):
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        raise SystemExit("usage: python -m client input.jsonl output.json")
    input_path, output_path = argv
    payloads = []
    with open(input_path, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                payloads.append(json.loads(line))
            except json.JSONDecodeError as exc:
                payloads.append({"__invalid_json__": True})
    result = convert_many(payloads)
    converted, errors = result[:2]
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(converted, handle, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    main()

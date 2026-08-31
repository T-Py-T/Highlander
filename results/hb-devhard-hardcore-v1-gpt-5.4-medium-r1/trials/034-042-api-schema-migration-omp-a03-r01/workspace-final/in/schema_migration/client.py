from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

AUDIT_PATH = Path(__file__).with_name("conversion_audit.json")
PII_KEYS = {
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "phone_number",
    "passport_number",
}
LEGACY_TOP_LEVEL_KEYS = {
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
V2_TOP_LEVEL_KEYS = {"orderId", "buyer", "lineItems", "shipping", "metadata"}


class ConversionError(ValueError):
    def __init__(self, path: str, error: str):
        super().__init__(error)
        self.path = path
        self.error = error


class AuditCounter:
    def __init__(self) -> None:
        self.pii_dropped_count = 0
        self.unknown_fields_count = 0


class WarningCollector:
    def __init__(self) -> None:
        self._warnings: list[dict[str, str]] = []

    def add(self, path: str, warning: str) -> None:
        self._warnings.append({"path": path, "warning": warning})

    def attach(self, index: int) -> list[dict[str, Any]]:
        return [{"index": index, **warning} for warning in self._warnings]


class _Missing:
    pass


MISSING = _Missing()


def _ensure_object(payload: Any, path: str = "$") -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ConversionError(path, "expected object")
    return payload


def _get_required(container: dict[str, Any], key: str, path: str) -> Any:
    if key not in container:
        raise ConversionError(path, "missing required field")
    return container[key]


def _non_empty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConversionError(path, "expected non-empty string")
    return value


def _to_int(value: Any, path: str) -> int:
    if isinstance(value, bool):
        raise ConversionError(path, "expected integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and (stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit())):
            return int(stripped)
    raise ConversionError(path, "expected integer")


def _normalize_shipping_method(value: Any) -> str:
    if value is None:
        return "standard"
    if isinstance(value, str) and not value.strip():
        return "standard"
    if isinstance(value, str):
        return value
    return str(value)


def _is_v2_payload(payload: dict[str, Any]) -> bool:
    return "orderId" in payload or {"buyer", "lineItems", "shipping"}.issubset(payload.keys())


def _copy_if_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConversionError(path, "expected object")
    return deepcopy(value)


def _convert_line_item(item: Any, path: str, *, quantity_key: str, price_key: str) -> dict[str, Any]:
    item_obj = _ensure_object(item, path)
    sku = _non_empty_string(_get_required(item_obj, "sku", f"{path}.sku"), f"{path}.sku")
    quantity = _to_int(_get_required(item_obj, quantity_key, f"{path}.{quantity_key}"), f"{path}.{quantity_key}")
    unit_price = _to_int(_get_required(item_obj, price_key, f"{path}.{price_key}"), f"{path}.{price_key}")
    return {"sku": sku, "quantity": quantity, "unitPriceCents": unit_price}


def _extract_unknown_fields(
    payload: dict[str, Any],
    known_keys: set[str],
    audit: AuditCounter,
    warnings: WarningCollector,
    *,
    prefix: str = "",
) -> dict[str, Any]:
    unknown: dict[str, Any] = {}
    for key, value in payload.items():
        if key in known_keys:
            continue
        full_path = f"{prefix}{key}" if prefix else key
        if key.lower() in PII_KEYS:
            audit.pii_dropped_count += 1
            warnings.add(full_path, "dropped pii field")
            continue
        unknown[key] = deepcopy(value)
        audit.unknown_fields_count += 1
    return unknown


def _convert_legacy(payload: dict[str, Any], audit: AuditCounter, warnings: WarningCollector) -> dict[str, Any]:
    order_id = payload.get("order_ref", payload.get("id", MISSING))
    if order_id is MISSING:
        raise ConversionError("id", "missing required field")
    order_id = _non_empty_string(order_id, "order_ref" if "order_ref" in payload else "id")

    if "customer" in payload:
        customer = _ensure_object(payload["customer"], "customer")
        buyer_id = _non_empty_string(_get_required(customer, "id", "customer.id"), "customer.id")
        display_name = _non_empty_string(_get_required(customer, "name", "customer.name"), "customer.name")
    else:
        buyer_id = _non_empty_string(_get_required(payload, "customer_id", "customer_id"), "customer_id")
        display_name = _non_empty_string(_get_required(payload, "customer_name", "customer_name"), "customer_name")

    raw_items = payload.get("lines", payload.get("items", MISSING))
    items_path = "lines" if "lines" in payload else "items"
    if raw_items is MISSING:
        raise ConversionError(items_path, "missing required field")
    if not isinstance(raw_items, list):
        raise ConversionError(items_path, "expected array")
    line_items = []
    for index, item in enumerate(raw_items):
        if items_path == "lines":
            line_items.append(_convert_line_item(item, f"lines[{index}]", quantity_key="qty", price_key="unit_price_cents" if "unit_price_cents" in _ensure_object(item, f"lines[{index}]") else "price_cents"))
        else:
            line_items.append(_convert_line_item(item, f"items[{index}]", quantity_key="qty", price_key="price_cents"))

    if not line_items:
        raise ConversionError(items_path, "must contain at least one item")

    shipping_source = payload.get("shipTo", payload.get("ship_to", MISSING))
    shipping_path = "shipTo" if "shipTo" in payload else "ship_to"
    if shipping_source is MISSING:
        raise ConversionError(shipping_path, "missing required field")
    shipping_obj = _ensure_object(shipping_source, shipping_path)
    country = _non_empty_string(_get_required(shipping_obj, "country", f"{shipping_path}.country"), f"{shipping_path}.country")

    postal_value = MISSING
    postal_path = ""
    for key in ("postal", "postalCode", "postal_code"):
        if key in shipping_obj:
            postal_value = shipping_obj[key]
            postal_path = f"{shipping_path}.{key}"
            break
    if postal_value is MISSING:
        raise ConversionError(f"{shipping_path}.postalCode", "missing required field")
    postal_code = _non_empty_string(postal_value, postal_path)

    method_source = payload["shipping_method"] if "shipping_method" in payload else payload.get("shipping")
    shipping_method = _normalize_shipping_method(method_source)

    unknown_fields = _extract_unknown_fields(payload, LEGACY_TOP_LEVEL_KEYS, audit, warnings)

    return {
        "orderId": order_id,
        "buyer": {"id": buyer_id, "displayName": display_name},
        "lineItems": line_items,
        "shipping": {
            "method": shipping_method,
            "address": {"country": country, "postalCode": postal_code},
        },
        "metadata": {
            "source": "legacy-v1",
            **({"unknownFields": unknown_fields} if unknown_fields else {}),
        },
    }


def _convert_v2(payload: dict[str, Any], audit: AuditCounter, warnings: WarningCollector) -> dict[str, Any]:
    order_id = _non_empty_string(_get_required(payload, "orderId", "orderId"), "orderId")

    buyer = _ensure_object(_get_required(payload, "buyer", "buyer"), "buyer")
    buyer_id = _non_empty_string(_get_required(buyer, "id", "buyer.id"), "buyer.id")
    display_name = _non_empty_string(_get_required(buyer, "displayName", "buyer.displayName"), "buyer.displayName")

    raw_line_items = _get_required(payload, "lineItems", "lineItems")
    if not isinstance(raw_line_items, list):
        raise ConversionError("lineItems", "expected array")
    if not raw_line_items:
        raise ConversionError("lineItems", "must contain at least one item")

    line_items: list[dict[str, Any]] = []
    for index, raw_item in enumerate(raw_line_items):
        item = _copy_if_mapping(raw_item, f"lineItems[{index}]")
        _non_empty_string(_get_required(item, "sku", f"lineItems[{index}].sku"), f"lineItems[{index}].sku")
        quantity = _to_int(_get_required(item, "quantity", f"lineItems[{index}].quantity"), f"lineItems[{index}].quantity")
        unit_price = _to_int(_get_required(item, "unitPriceCents", f"lineItems[{index}].unitPriceCents"), f"lineItems[{index}].unitPriceCents")
        item["quantity"] = quantity
        item["unitPriceCents"] = unit_price
        line_items.append(item)

    shipping = _ensure_object(_get_required(payload, "shipping", "shipping"), "shipping")
    address = _ensure_object(_get_required(shipping, "address", "shipping.address"), "shipping.address")
    country = _non_empty_string(_get_required(address, "country", "shipping.address.country"), "shipping.address.country")
    postal_code = _non_empty_string(_get_required(address, "postalCode", "shipping.address.postalCode"), "shipping.address.postalCode")
    shipping_method = _normalize_shipping_method(shipping.get("method"))

    metadata = _copy_if_mapping(payload.get("metadata", {}), "metadata")
    source = metadata.get("source")
    if source is None:
        source = "public-v2"
    source = _non_empty_string(source, "metadata.source")

    existing_unknown = metadata.get("unknownFields")
    if existing_unknown is None:
        unknown_fields: dict[str, Any] = {}
    elif isinstance(existing_unknown, dict):
        unknown_fields = deepcopy(existing_unknown)
    else:
        raise ConversionError("metadata.unknownFields", "expected object")

    extra_metadata = _extract_unknown_fields(metadata, {"source", "unknownFields"}, audit, warnings, prefix="metadata.")
    for key, value in extra_metadata.items():
        unknown_fields[key] = value

    top_level_unknown = _extract_unknown_fields(payload, V2_TOP_LEVEL_KEYS, audit, warnings)
    for key, value in top_level_unknown.items():
        unknown_fields[key] = value

    result_metadata: dict[str, Any] = {"source": source}
    if unknown_fields:
        result_metadata["unknownFields"] = unknown_fields

    return {
        "orderId": order_id,
        "buyer": {"id": buyer_id, "displayName": display_name},
        "lineItems": line_items,
        "shipping": {"method": shipping_method, "address": {"country": country, "postalCode": postal_code}},
        "metadata": result_metadata,
    }


def convert_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert legacy or v2 payloads to the public v2 API shape."""
    payload_obj = _ensure_object(payload)
    audit = AuditCounter()
    warnings = WarningCollector()
    if _is_v2_payload(payload_obj):
        return _convert_v2(payload_obj, audit, warnings)
    return _convert_legacy(payload_obj, audit, warnings)


def _write_audit(converted_count: int, error_count: int, warning_count: int, audit: AuditCounter) -> None:
    AUDIT_PATH.write_text(
        json.dumps(
            {
                "converted_count": converted_count,
                "error_count": error_count,
                "warning_count": warning_count,
                "pii_dropped_count": audit.pii_dropped_count,
                "unknown_fields_count": audit.unknown_fields_count,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def convert_many(payloads: list[dict[str, Any]]):
    converted: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings_out: list[dict[str, Any]] = []
    audit = AuditCounter()

    for index, payload in enumerate(payloads):
        collector = WarningCollector()
        try:
            payload_obj = _ensure_object(payload)
            if _is_v2_payload(payload_obj):
                converted.append(_convert_v2(payload_obj, audit, collector))
            else:
                converted.append(_convert_legacy(payload_obj, audit, collector))
        except ConversionError as exc:
            errors.append({"index": index, "path": exc.path, "error": exc.error})
        warnings_out.extend(collector.attach(index))

    _write_audit(len(converted), len(errors), len(warnings_out), audit)
    if warnings_out:
        return converted, errors, warnings_out
    return converted, errors


def summarize_order(v2_payload: dict[str, Any]) -> str:
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def _load_jsonl(path: str) -> list[Any]:
    payloads = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payloads.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid json on line {line_number}: {exc.msg}") from exc
    return payloads


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("usage: python -m client input.jsonl output.json", file=sys.stderr)
        return 2

    payloads = _load_jsonl(args[0])
    result = convert_many(payloads)
    converted = result[0]
    with open(args[1], "w", encoding="utf-8") as handle:
        json.dump(converted, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return 0 if not result[1] else 1


if __name__ == "__main__":
    raise SystemExit(main())

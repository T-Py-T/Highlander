import json
import sys
from pathlib import Path


AUDIT_PATH = Path(__file__).with_name("conversion_audit.json")
PII_EXCLUDED_KEYS = {
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "phone_number",
    "passport_number",
}
V2_METADATA_RESERVED_KEYS = {"source", "unknownFields"}
LEGACY_TOP_LEVEL_KNOWN_KEYS = {
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
    def __init__(self, path, error):
        super().__init__(error)
        self.path = path
        self.error = error


def _is_v2_payload(payload):
    return isinstance(payload, dict) and "orderId" in payload


def _require_dict(value, path):
    if not isinstance(value, dict):
        raise ConversionError(path, "expected object")
    return value


def _require_non_empty(value, path):
    if value is None:
        raise ConversionError(path, "missing required field")
    if isinstance(value, str) and value.strip() == "":
        raise ConversionError(path, "missing required field")
    return value


def _coerce_int(value, path):
    if isinstance(value, bool):
        raise ConversionError(path, "expected integer")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ConversionError(path, "expected integer")


def _normalize_shipping_method(value):
    if value is None:
        return "standard"
    if isinstance(value, str) and value.strip() == "":
        return "standard"
    return value


def _extract_legacy_buyer(payload):
    if isinstance(payload.get("customer"), dict):
        customer = payload["customer"]
        buyer_id = _require_non_empty(customer.get("id"), "customer.id")
        display_name = _require_non_empty(customer.get("name"), "customer.name")
        return {"id": buyer_id, "displayName": display_name}
    buyer_id = _require_non_empty(payload.get("customer_id"), "customer_id")
    display_name = _require_non_empty(payload.get("customer_name"), "customer_name")
    return {"id": buyer_id, "displayName": display_name}


def _extract_legacy_shipping(payload):
    shipping_method = _normalize_shipping_method(
        payload.get("shipping_method", payload.get("shipping"))
    )
    if not isinstance(shipping_method, str):
        raise ConversionError("shipping_method", "expected string")

    source_address = payload.get("ship_to")
    address_path = "ship_to"
    if source_address is None:
        source_address = payload.get("shipTo")
        address_path = "shipTo"
    source_address = _require_dict(source_address, address_path)

    country = _require_non_empty(source_address.get("country"), f"{address_path}.country")
    postal_code = source_address.get("postal")
    postal_path = f"{address_path}.postal"
    if postal_code in (None, ""):
        postal_code = source_address.get("postalCode")
        postal_path = f"{address_path}.postalCode"
    if postal_code in (None, ""):
        postal_code = source_address.get("postal_code")
        postal_path = f"{address_path}.postal_code"
    postal_code = _require_non_empty(postal_code, postal_path)

    return {
        "method": shipping_method,
        "address": {"country": country, "postalCode": postal_code},
    }


def _convert_legacy_line_items(payload):
    line_source = payload.get("items")
    source_name = "items"
    if line_source is None:
        line_source = payload.get("lines")
        source_name = "lines"
    if not isinstance(line_source, list):
        raise ConversionError(source_name, "expected array")
    if not line_source:
        raise ConversionError(source_name, "must contain at least one item")

    line_items = []
    for index, item in enumerate(line_source):
        item_path = f"{source_name}[{index}]"
        item = _require_dict(item, item_path)
        sku = _require_non_empty(item.get("sku"), f"{item_path}.sku")
        quantity = _coerce_int(item.get("qty"), f"{item_path}.qty")
        unit_price = item.get("price_cents")
        price_path = f"{item_path}.price_cents"
        if unit_price is None:
            unit_price = item.get("unit_price_cents")
            price_path = f"{item_path}.unit_price_cents"
        unit_price = _coerce_int(unit_price, price_path)
        line_items.append(
            {"sku": sku, "quantity": quantity, "unitPriceCents": unit_price}
        )
    return line_items


def _collect_unknown_fields(payload, stats, warnings=None, index=None):
    unknown_fields = {}
    for key, value in payload.items():
        if key in LEGACY_TOP_LEVEL_KNOWN_KEYS:
            continue
        if key in PII_EXCLUDED_KEYS:
            stats["pii_dropped_count"] += 1
            if warnings is not None:
                warnings.append(
                    {"index": index, "path": key, "warning": "dropped excluded PII field"}
                )
            continue
        unknown_fields[key] = value
        stats["unknown_fields_count"] += 1
        if warnings is not None:
            warnings.append(
                {"index": index, "path": key, "warning": "preserved unknown field"}
            )
    return unknown_fields


def _convert_v2_payload(payload, stats=None, warnings=None, index=None):
    stats = stats or {"pii_dropped_count": 0, "unknown_fields_count": 0}
    order_id = _require_non_empty(payload.get("orderId"), "orderId")
    buyer = _require_dict(payload.get("buyer"), "buyer")
    _require_non_empty(buyer.get("id"), "buyer.id")
    _require_non_empty(buyer.get("displayName"), "buyer.displayName")

    line_items = payload.get("lineItems")
    if not isinstance(line_items, list):
        raise ConversionError("lineItems", "expected array")
    if not line_items:
        raise ConversionError("lineItems", "must contain at least one item")

    shipping = _require_dict(payload.get("shipping"), "shipping")
    address = _require_dict(shipping.get("address"), "shipping.address")
    _require_non_empty(address.get("country"), "shipping.address.country")
    _require_non_empty(address.get("postalCode"), "shipping.address.postalCode")

    metadata = payload.get("metadata")
    if metadata is None:
        metadata = {}
    metadata = _require_dict(metadata, "metadata")

    unknown_fields = metadata.get("unknownFields")
    unknown_fields_present = "unknownFields" in metadata
    if unknown_fields is None:
        unknown_fields = {}
    unknown_fields = _require_dict(unknown_fields, "metadata.unknownFields")
    unknown_fields = dict(unknown_fields)
    stats["unknown_fields_count"] += len(unknown_fields)

    for key, value in metadata.items():
        if key not in V2_METADATA_RESERVED_KEYS:
            unknown_fields[key] = value
            stats["unknown_fields_count"] += 1
            if warnings is not None:
                warnings.append(
                    {
                        "index": index,
                        "path": f"metadata.{key}",
                        "warning": "preserved metadata field under metadata.unknownFields",
                    }
                )

    converted_metadata = {"source": metadata.get("source", "public-v2")}
    if unknown_fields or unknown_fields_present:
        converted_metadata["unknownFields"] = unknown_fields

    return {
        "orderId": order_id,
        "buyer": dict(buyer),
        "lineItems": list(line_items),
        "shipping": {
            "method": _normalize_shipping_method(shipping.get("method")),
            "address": dict(address),
        },
        "metadata": converted_metadata,
    }


def _convert_legacy_payload(payload, stats=None, warnings=None, index=None):
    stats = stats or {"pii_dropped_count": 0, "unknown_fields_count": 0}
    order_id = payload.get("order_ref")
    order_path = "order_ref"
    if order_id in (None, ""):
        order_id = payload.get("id")
        order_path = "id"
    order_id = _require_non_empty(order_id, order_path)

    converted = {
        "orderId": order_id,
        "buyer": _extract_legacy_buyer(payload),
        "lineItems": _convert_legacy_line_items(payload),
        "shipping": _extract_legacy_shipping(payload),
        "metadata": {"source": "legacy-v1"},
    }

    unknown_fields = _collect_unknown_fields(payload, stats, warnings, index)
    if unknown_fields:
        converted["metadata"]["unknownFields"] = unknown_fields
    return converted


def convert_order(payload):
    """Convert a legacy order payload or normalize a v2 payload."""
    if not isinstance(payload, dict):
        raise ConversionError("$", "expected object")
    if _is_v2_payload(payload):
        return _convert_v2_payload(payload)
    return _convert_legacy_payload(payload)


def _write_audit(stats):
    AUDIT_PATH.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")


def convert_many(payloads):
    converted = []
    errors = []
    warnings = []
    stats = {
        "converted_count": 0,
        "error_count": 0,
        "warning_count": 0,
        "pii_dropped_count": 0,
        "unknown_fields_count": 0,
    }

    for index, payload in enumerate(payloads):
        try:
            if not isinstance(payload, dict):
                raise ConversionError("$", "expected object")
            if _is_v2_payload(payload):
                converted_payload = _convert_v2_payload(payload, stats, warnings, index)
            else:
                converted_payload = _convert_legacy_payload(payload, stats, warnings, index)
            converted.append(converted_payload)
            stats["converted_count"] += 1
        except ConversionError as exc:
            errors.append({"index": index, "path": exc.path, "error": exc.error})
        except Exception as exc:
            errors.append({"index": index, "path": "$", "error": str(exc)})

    stats["error_count"] = len(errors)
    stats["warning_count"] = len(warnings)
    _write_audit(stats)
    return converted, errors, warnings


def summarize_order(v2_payload):
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def _read_jsonl(path):
    payloads = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payloads.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ConversionError(f"line {line_number}", f"invalid JSON: {exc.msg}")
    return payloads


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print("Usage: python -m client input.jsonl output.json", file=sys.stderr)
        return 2

    input_path, output_path = argv
    try:
        payloads = _read_jsonl(input_path)
        converted, errors, warnings = convert_many(payloads)
    except ConversionError as exc:
        print(json.dumps({"path": exc.path, "error": exc.error}), file=sys.stderr)
        return 1

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(converted, handle, indent=2)
        handle.write("\n")

    summary = {
        "converted_count": len(converted),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "audit_path": str(AUDIT_PATH),
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

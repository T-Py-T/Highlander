import json
import sys
from copy import deepcopy
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


class ConversionError(ValueError):
    def __init__(self, path, error):
        super().__init__(error)
        self.path = path
        self.error = error


def _is_blank(value):
    return value is None or (isinstance(value, str) and value.strip() == "")


def _require_dict(value, path):
    if not isinstance(value, dict):
        raise ConversionError(path, "must be an object")
    return value


def _require_list(value, path):
    if not isinstance(value, list):
        raise ConversionError(path, "must be a list")
    return value


def _require_non_blank(value, path):
    if _is_blank(value):
        raise ConversionError(path, "missing required value")
    return value


def _coerce_int(value, path):
    if isinstance(value, bool):
        raise ConversionError(path, "must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and (stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit())):
            return int(stripped)
    raise ConversionError(path, "must be an integer")


def _extract_source(payload):
    if isinstance(payload, dict) and "orderId" in payload:
        return payload.get("metadata", {}).get("source") or "public-v2"
    if isinstance(payload, dict) and "order_ref" in payload:
        return "legacy-v1.2"
    if isinstance(payload, dict) and "shipping" in payload and "items" in payload:
        return "legacy-v1.1"
    return "legacy-v1"


def _default_shipping_method(method, warnings, index, path):
    if _is_blank(method):
        warnings.append({"index": index, "path": path, "warning": 'shipping method defaulted to "standard"'})
        return "standard"
    return method


def _split_unknown_fields(extra_fields, warnings, index):
    unknown = {}
    pii_dropped = 0
    for key, value in extra_fields.items():
        if key in PII_EXCLUDED_KEYS:
            pii_dropped += 1
            warnings.append({"index": index, "path": key, "warning": "dropped excluded PII field"})
        else:
            unknown[key] = value
    return unknown, pii_dropped


def _convert_line_item(item, index, source_key):
    item = _require_dict(item, f"{source_key}[{index}]")
    sku = _require_non_blank(item.get("sku"), f"{source_key}[{index}].sku")
    qty = _coerce_int(item.get("qty"), f"{source_key}[{index}].qty")
    price_key = "unit_price_cents" if "unit_price_cents" in item else "price_cents"
    price = _coerce_int(item.get(price_key), f"{source_key}[{index}].{price_key}")
    return {
        "sku": sku,
        "quantity": qty,
        "unitPriceCents": price,
    }


def _convert_v2(payload, warnings, index):
    payload = _require_dict(payload, "payload")
    result = deepcopy(payload)

    order_id = _require_non_blank(result.get("orderId"), "orderId")
    result["orderId"] = order_id

    buyer = _require_dict(result.get("buyer"), "buyer")
    buyer_id = _require_non_blank(buyer.get("id"), "buyer.id")
    buyer_name = _require_non_blank(buyer.get("displayName"), "buyer.displayName")
    result["buyer"] = {"id": buyer_id, "displayName": buyer_name}

    line_items = _require_list(result.get("lineItems"), "lineItems")
    for item_index, item in enumerate(line_items):
        _require_dict(item, f"lineItems[{item_index}]")
        _require_non_blank(item.get("sku"), f"lineItems[{item_index}].sku")
        _coerce_int(item.get("quantity"), f"lineItems[{item_index}].quantity")
        _coerce_int(item.get("unitPriceCents"), f"lineItems[{item_index}].unitPriceCents")

    shipping = _require_dict(result.get("shipping"), "shipping")
    address = _require_dict(shipping.get("address"), "shipping.address")
    _require_non_blank(address.get("country"), "shipping.address.country")
    _require_non_blank(address.get("postalCode"), "shipping.address.postalCode")
    shipping["method"] = _default_shipping_method(shipping.get("method"), warnings, index, "shipping.method")

    metadata = result.get("metadata")
    if metadata is None:
        metadata = {}
    metadata = _require_dict(metadata, "metadata")
    metadata.setdefault("source", "public-v2")
    unknown_fields = metadata.get("unknownFields")
    if unknown_fields is None:
        unknown_fields = {}
    unknown_fields = _require_dict(unknown_fields, "metadata.unknownFields")
    metadata["unknownFields"] = unknown_fields
    result["metadata"] = metadata
    return result


def _convert_legacy(payload, warnings, index):
    payload = _require_dict(payload, "payload")
    source = _extract_source(payload)

    if "order_ref" in payload:
        order_id = _require_non_blank(payload.get("order_ref"), "order_ref")
    else:
        order_id = _require_non_blank(payload.get("id"), "id")

    if "customer" in payload:
        customer = _require_dict(payload.get("customer"), "customer")
        buyer_id = _require_non_blank(customer.get("id"), "customer.id")
        buyer_name = _require_non_blank(customer.get("name"), "customer.name")
    else:
        buyer_id = _require_non_blank(payload.get("customer_id"), "customer_id")
        buyer_name = _require_non_blank(payload.get("customer_name"), "customer_name")

    raw_items = payload.get("lines") if "lines" in payload else payload.get("items")
    item_path = "lines" if "lines" in payload else "items"
    items = _require_list(raw_items, item_path)
    if not items:
        raise ConversionError(item_path, "must contain at least one item")
    line_items = [_convert_line_item(item, item_index, item_path) for item_index, item in enumerate(items)]

    raw_ship_to = payload.get("shipTo") if "shipTo" in payload else payload.get("ship_to")
    ship_path = "shipTo" if "shipTo" in payload else "ship_to"
    ship_to = _require_dict(raw_ship_to, ship_path)
    country = _require_non_blank(ship_to.get("country"), f"{ship_path}.country")
    postal = ship_to.get("postal")
    if postal is None:
        postal = ship_to.get("postalCode")
    if postal is None:
        postal = ship_to.get("postal_code")
    postal = _require_non_blank(postal, f"{ship_path}.postal")

    shipping_method = payload.get("shipping_method")
    if shipping_method is None and "shipping" in payload and not isinstance(payload.get("shipping"), dict):
        shipping_method = payload.get("shipping")
    shipping_method = _default_shipping_method(shipping_method, warnings, index, "shipping_method")

    known_top_level = {
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
    extra_fields = {key: value for key, value in payload.items() if key not in known_top_level}
    unknown_fields, pii_dropped = _split_unknown_fields(extra_fields, warnings, index)

    result = {
        "orderId": order_id,
        "buyer": {"id": buyer_id, "displayName": buyer_name},
        "lineItems": line_items,
        "shipping": {
            "method": shipping_method,
            "address": {"country": country, "postalCode": postal},
        },
        "metadata": {"source": source},
    }
    if unknown_fields:
        result["metadata"]["unknownFields"] = unknown_fields
    result["_conversion_stats"] = {
        "pii_dropped_count": pii_dropped,
        "unknown_fields_count": len(unknown_fields),
    }
    return result


def _pop_stats(converted_payload):
    stats = converted_payload.pop("_conversion_stats", None)
    if not stats:
        stats = {"pii_dropped_count": 0, "unknown_fields_count": 0}
    return stats


def convert_order(payload):
    """Convert a legacy or v2 order payload to the v2 public API shape."""
    warnings = []
    if isinstance(payload, dict) and "orderId" in payload:
        return _convert_v2(payload, warnings, index=0)
    converted = _convert_legacy(payload, warnings, index=0)
    _pop_stats(converted)
    return converted


def convert_many(payloads):
    converted = []
    errors = []
    warnings = []
    pii_dropped_count = 0
    unknown_fields_count = 0

    for index, payload in enumerate(payloads):
        item_warnings = []
        try:
            if isinstance(payload, dict) and "orderId" in payload:
                converted_payload = _convert_v2(payload, item_warnings, index)
            else:
                converted_payload = _convert_legacy(payload, item_warnings, index)
            stats = _pop_stats(converted_payload)
            pii_dropped_count += stats.get("pii_dropped_count", 0)
            unknown_fields_count += stats.get("unknown_fields_count", 0)
            converted.append(converted_payload)
            warnings.extend(item_warnings)
        except ConversionError as exc:
            errors.append({"index": index, "path": exc.path, "error": exc.error})
        except Exception as exc:
            errors.append({"index": index, "path": "payload", "error": str(exc)})

    audit = {
        "converted_count": len(converted),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "pii_dropped_count": pii_dropped_count,
        "unknown_fields_count": unknown_fields_count,
    }
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if warnings:
        return converted, errors, warnings
    return converted, errors


def summarize_order(v2_payload):
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def _load_jsonl(path):
    payloads = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payloads.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ConversionError(f"input[{line_number}]", f"invalid JSON: {exc.msg}") from exc
    return payloads


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print("Usage: python -m client input.jsonl output.json", file=sys.stderr)
        return 2

    input_path, output_path = argv
    try:
        payloads = _load_jsonl(input_path)
        result = convert_many(payloads)
        converted = result[0]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(converted, handle, indent=2, sort_keys=True)
            handle.write("\n")
        errors = result[1]
        if errors:
            print(json.dumps({"errors": errors}, indent=2), file=sys.stderr)
            return 1
        return 0
    except ConversionError as exc:
        print(json.dumps({"errors": [{"index": None, "path": exc.path, "error": exc.error}]}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

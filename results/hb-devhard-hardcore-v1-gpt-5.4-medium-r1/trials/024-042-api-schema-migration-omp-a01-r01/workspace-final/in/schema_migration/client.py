import json
import sys
from collections.abc import Sequence
from pathlib import Path


PII_EXCLUDED_KEYS = {
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "phone_number",
    "passport_number",
}

V2_TOP_LEVEL_KEYS = {"orderId", "buyer", "lineItems", "shipping", "metadata"}
V2_METADATA_KEYS = {"source", "unknownFields"}
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


class ConversionError(ValueError):
    def __init__(self, path, error):
        super().__init__(error)
        self.path = path
        self.error = error


class ConversionResult(Sequence):
    def __init__(self, converted, errors, warnings):
        self.converted = converted
        self.errors = errors
        self.warnings = warnings

    def __getitem__(self, index):
        if index == 0:
            return self.converted
        if index == 1:
            return self.errors
        if index == 2:
            return self.warnings
        raise IndexError(index)

    def __len__(self):
        return 3

    def __iter__(self):
        yield self.converted
        yield self.errors


def _raise(path, error):
    raise ConversionError(path, error)


def _require_mapping(value, path):
    if not isinstance(value, dict):
        _raise(path, "must be an object")
    return value


def _require_string(value, path):
    if value is None:
        _raise(path, "missing value")
    if not isinstance(value, str):
        _raise(path, "must be a string")
    if not value.strip():
        _raise(path, "must not be blank")
    return value


def _require_list(value, path):
    if not isinstance(value, list):
        _raise(path, "must be an array")
    if not value:
        _raise(path, "must not be empty")
    return value


def _coerce_int(value, path):
    if isinstance(value, bool):
        _raise(path, "must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and (stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit())):
            return int(stripped)
    _raise(path, "must be an integer")


def _normalize_shipping_method(method):
    if method is None:
        return "standard"
    if isinstance(method, str) and not method.strip():
        return "standard"
    return method


def _is_v2_payload(payload):
    return isinstance(payload, dict) and (
        "orderId" in payload
        or {"buyer", "lineItems", "shipping", "metadata"}.issubset(payload)
    )


def _detect_legacy_source(payload, shipping_payload):
    if "order_ref" in payload or "customer" in payload or "lines" in payload or "shipTo" in payload:
        return "legacy-v1.2"
    if "shipping" in payload or ("ship_to" in payload and isinstance(shipping_payload, dict) and "postalCode" in shipping_payload):
        return "legacy-v1.1"
    return "legacy-v1"


def _empty_unknown_bucket():
    return {}


def _merge_unknown(target, key, value):
    if value in ({}, [], None):
        return
    target[key] = value


def _collect_unknown_top_level(payload, consumed_keys, warnings, stats, index):
    unknown = _empty_unknown_bucket()
    for key, value in payload.items():
        if key in consumed_keys:
            continue
        if key.lower() in PII_EXCLUDED_KEYS:
            stats["pii_dropped_count"] += 1
            warnings.append({"index": index, "path": key, "warning": f"dropped PII-like field '{key}'"})
            continue
        unknown[key] = value
        stats["unknown_fields_count"] += 1
    return unknown


def _extract_legacy_buyer(payload, consumed_keys):
    if "customer" in payload:
        customer = _require_mapping(payload["customer"], "customer")
        consumed_keys.add("customer")
        buyer = {
            "id": _require_string(customer.get("id"), "customer.id"),
            "displayName": _require_string(customer.get("name"), "customer.name"),
        }
        customer_unknown = {}
        for key, value in customer.items():
            if key not in {"id", "name"}:
                customer_unknown[key] = value
        return buyer, customer_unknown
    buyer = {
        "id": _require_string(payload.get("customer_id"), "customer_id"),
        "displayName": _require_string(payload.get("customer_name"), "customer_name"),
    }
    consumed_keys.update({"customer_id", "customer_name"})
    return buyer, {}


def _convert_legacy_line_items(payload, consumed_keys):
    source_key = "lines" if "lines" in payload else "items"
    items = _require_list(payload.get(source_key), source_key)
    consumed_keys.add(source_key)
    converted = []
    unknown = []
    for idx, item in enumerate(items):
        item_path = f"{source_key}[{idx}]"
        item = _require_mapping(item, item_path)
        if "unit_price_cents" in item:
            price_key = "unit_price_cents"
        else:
            price_key = "price_cents"
        converted_item = {
            "sku": _require_string(item.get("sku"), f"{item_path}.sku"),
            "quantity": _coerce_int(item.get("qty"), f"{item_path}.qty"),
            "unitPriceCents": _coerce_int(item.get(price_key), f"{item_path}.{price_key}"),
        }
        converted.append(converted_item)
        extra = {}
        for key, value in item.items():
            if key not in {"sku", "qty", "price_cents", "unit_price_cents"}:
                extra[key] = value
        unknown.append(extra)
    if any(extra for extra in unknown):
        return converted, unknown
    return converted, []


def _extract_legacy_shipping(payload, consumed_keys):
    if "shipTo" in payload:
        ship = _require_mapping(payload["shipTo"], "shipTo")
        consumed_keys.add("shipTo")
        postal = ship.get("postal_code")
        postal_path = "shipTo.postal_code"
    else:
        ship = _require_mapping(payload.get("ship_to"), "ship_to")
        consumed_keys.add("ship_to")
        if "postalCode" in ship:
            postal = ship.get("postalCode")
            postal_path = "ship_to.postalCode"
        else:
            postal = ship.get("postal")
            postal_path = "ship_to.postal"
    address = {
        "country": _require_string(ship.get("country"), f"{'shipTo' if 'shipTo' in payload else 'ship_to'}.country"),
        "postalCode": _require_string(postal, postal_path),
    }
    extra = {}
    for key, value in ship.items():
        if key not in {"country", "postal", "postalCode", "postal_code"}:
            extra[key] = value
    return address, extra


def _extract_legacy_unknowns(payload, consumed_keys, customer_unknown, line_unknown, shipping_unknown, warnings, stats, index):
    unknown = _collect_unknown_top_level(payload, consumed_keys, warnings, stats, index)
    _merge_unknown(unknown, "customer", customer_unknown)
    if line_unknown and any(extra for extra in line_unknown):
        unknown["lineItems"] = line_unknown
        stats["unknown_fields_count"] += sum(1 for extra in line_unknown if extra)
    _merge_unknown(unknown, "shipping", shipping_unknown)
    if customer_unknown:
        stats["unknown_fields_count"] += 1
    if shipping_unknown:
        stats["unknown_fields_count"] += 1
    return unknown


def _convert_legacy(payload, index=None, warnings=None, stats=None):
    consumed_keys = set()
    warnings = warnings if warnings is not None else []
    stats = stats if stats is not None else {
        "pii_dropped_count": 0,
        "unknown_fields_count": 0,
    }
    source_shipping = payload.get("shipTo") if "shipTo" in payload else payload.get("ship_to")
    source = _detect_legacy_source(payload, source_shipping if isinstance(source_shipping, dict) else {})

    order_key = "order_ref" if "order_ref" in payload else "id"
    consumed_keys.add(order_key)
    buyer, customer_unknown = _extract_legacy_buyer(payload, consumed_keys)
    line_items, line_unknown = _convert_legacy_line_items(payload, consumed_keys)
    address, shipping_unknown = _extract_legacy_shipping(payload, consumed_keys)

    if "shipping_method" in payload:
        shipping_path = "shipping_method"
        shipping_method = payload.get("shipping_method")
        consumed_keys.add("shipping_method")
    elif "shipping" in payload:
        shipping_path = "shipping"
        shipping_method = payload.get("shipping")
        consumed_keys.add("shipping")
    else:
        shipping_path = "shipping_method"
        shipping_method = None

    method = _normalize_shipping_method(shipping_method)
    if method is not None and not isinstance(method, str):
        _raise(shipping_path, "must be a string")

    unknown = _extract_legacy_unknowns(
        payload,
        consumed_keys,
        customer_unknown,
        line_unknown,
        shipping_unknown,
        warnings,
        stats,
        index,
    )

    metadata = {"source": source}
    if unknown:
        metadata["unknownFields"] = unknown

    return {
        "orderId": _require_string(payload.get(order_key), order_key),
        "buyer": buyer,
        "lineItems": line_items,
        "shipping": {"method": method, "address": address},
        "metadata": metadata,
    }


def _normalize_v2_metadata(payload, metadata, warnings, stats, index):
    unknown = {}
    existing_unknown = metadata.get("unknownFields")
    if existing_unknown is None:
        existing_unknown = {}
    else:
        existing_unknown = _require_mapping(existing_unknown, "metadata.unknownFields")
        unknown.update(existing_unknown)

    for key, value in metadata.items():
        if key in V2_METADATA_KEYS:
            continue
        unknown[key] = value
        stats["unknown_fields_count"] += 1

    for key, value in payload.items():
        if key in V2_TOP_LEVEL_KEYS:
            continue
        if key.lower() in PII_EXCLUDED_KEYS:
            stats["pii_dropped_count"] += 1
            warnings.append({"index": index, "path": key, "warning": f"dropped PII-like field '{key}'"})
            continue
        unknown[key] = value
        stats["unknown_fields_count"] += 1

    result = {"source": _require_string(metadata.get("source"), "metadata.source")}
    if unknown:
        result["unknownFields"] = unknown
    elif "unknownFields" in metadata:
        result["unknownFields"] = {}
    return result


def _normalize_v2(payload, index=None, warnings=None, stats=None):
    warnings = warnings if warnings is not None else []
    stats = stats if stats is not None else {
        "pii_dropped_count": 0,
        "unknown_fields_count": 0,
    }
    buyer = _require_mapping(payload.get("buyer"), "buyer")
    shipping = _require_mapping(payload.get("shipping"), "shipping")
    address = _require_mapping(shipping.get("address"), "shipping.address")
    line_items = _require_list(payload.get("lineItems"), "lineItems")
    metadata = _require_mapping(payload.get("metadata"), "metadata")

    normalized_shipping = {
        "method": _normalize_shipping_method(shipping.get("method")),
        "address": {
            "country": _require_string(address.get("country"), "shipping.address.country"),
            "postalCode": _require_string(address.get("postalCode"), "shipping.address.postalCode"),
        },
    }
    if normalized_shipping["method"] is not None and not isinstance(normalized_shipping["method"], str):
        _raise("shipping.method", "must be a string")

    normalized = {
        "orderId": _require_string(payload.get("orderId"), "orderId"),
        "buyer": {
            "id": _require_string(buyer.get("id"), "buyer.id"),
            "displayName": _require_string(buyer.get("displayName"), "buyer.displayName"),
        },
        "lineItems": line_items,
        "shipping": normalized_shipping,
        "metadata": _normalize_v2_metadata(payload, metadata, warnings, stats, index),
    }
    return normalized


def convert_order(payload):
    """Convert legacy order payloads to the public v2 API shape."""
    payload = _require_mapping(payload, "payload")
    if _is_v2_payload(payload):
        return _normalize_v2(payload)
    return _convert_legacy(payload)


def _audit_path():
    return Path(__file__).with_name("conversion_audit.json")


def _write_audit(audit):
    _audit_path().write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")


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
            converted.append(
                _normalize_v2(payload, index=index, warnings=warnings, stats=stats)
                if _is_v2_payload(payload)
                else _convert_legacy(payload, index=index, warnings=warnings, stats=stats)
            )
            stats["converted_count"] += 1
        except ConversionError as exc:
            errors.append({"index": index, "path": exc.path, "error": exc.error})
        except Exception as exc:
            errors.append({"index": index, "path": "payload", "error": str(exc)})
    stats["error_count"] = len(errors)
    stats["warning_count"] = len(warnings)
    _write_audit(stats)
    return ConversionResult(converted, errors, warnings)


def summarize_order(v2_payload):
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def _read_jsonl(path):
    payloads = []
    with open(path, encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payloads.append(json.loads(line))
            except json.JSONDecodeError as exc:
                _raise(f"input[{line_number}]", f"invalid JSON: {exc.msg}")
    return payloads


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        raise SystemExit("usage: python -m client input.jsonl output.json")
    input_path, output_path = argv
    payloads = _read_jsonl(input_path)
    result = convert_many(payloads)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(result[0], handle, indent=2, sort_keys=True)
        handle.write("\n")
    if result[1]:
        sys.stderr.write(json.dumps(result[1], indent=2, sort_keys=True) + "\n")
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

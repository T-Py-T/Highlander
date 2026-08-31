import json
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


class ConversionResult:
    def __init__(self, converted, errors, warnings):
        self.converted = converted
        self.errors = errors
        self.warnings = warnings

    def __iter__(self):
        yield self.converted
        yield self.errors

    def __getitem__(self, index):
        if index == 0:
            return self.converted
        if index == 1:
            return self.errors
        if index == 2:
            return self.warnings
        raise IndexError(index)

    def __len__(self):
        return 2


def _require_mapping(payload, path):
    if not isinstance(payload, dict):
        raise ConversionError(path, "expected object")
    return payload


def _require_value(value, path):
    if value is None or value == "":
        raise ConversionError(path, "missing required value")
    return value


def _to_int(value, path):
    if isinstance(value, bool):
        raise ConversionError(path, "expected integer")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ConversionError(path, "expected integer")


def _normalize_shipping_method(value):
    if value is None:
        return "standard"
    if isinstance(value, str) and not value.strip():
        return "standard"
    return value


def _detect_source(payload):
    if "orderId" in payload and "buyer" in payload and "lineItems" in payload and "shipping" in payload:
        return "public-v2"
    if "order_ref" in payload or "customer" in payload or "lines" in payload or "shipTo" in payload:
        return "legacy-v1.2"
    if "shipping" in payload or ("ship_to" in payload and isinstance(payload.get("ship_to"), dict) and "postalCode" in payload["ship_to"]):
        return "legacy-v1.1"
    return "legacy-v1"


def _extract_unknown_fields(payload, known_keys, stats, warnings, index=None):
    unknown = {}
    for key, value in payload.items():
        if key in known_keys:
            continue
        if key.lower() in PII_EXCLUDED_KEYS:
            stats["pii_dropped_count"] += 1
            warnings.append({
                "index": index,
                "path": key,
                "warning": "dropped excluded PII field",
            })
            continue
        unknown[key] = deepcopy(value)
        stats["unknown_fields_count"] += 1
    return unknown


def _convert_line_item(item, path, legacy=True):
    item = _require_mapping(item, path)
    sku = _require_value(item.get("sku"), f"{path}.sku")
    if legacy:
        quantity = _to_int(_require_value(item.get("qty"), f"{path}.qty"), f"{path}.qty")
        raw_price = item.get("price_cents")
        price_path = f"{path}.price_cents"
        if raw_price is None and "unit_price_cents" in item:
            raw_price = item.get("unit_price_cents")
            price_path = f"{path}.unit_price_cents"
        unit_price_cents = _to_int(_require_value(raw_price, price_path), price_path)
        return {
            "sku": sku,
            "quantity": quantity,
            "unitPriceCents": unit_price_cents,
        }

    quantity = _to_int(_require_value(item.get("quantity"), f"{path}.quantity"), f"{path}.quantity")
    unit_price_cents = _to_int(
        _require_value(item.get("unitPriceCents"), f"{path}.unitPriceCents"),
        f"{path}.unitPriceCents",
    )
    converted = deepcopy(item)
    converted["sku"] = sku
    converted["quantity"] = quantity
    converted["unitPriceCents"] = unit_price_cents
    return converted


def _convert_legacy(payload, source, stats, warnings, index=None):
    if source == "legacy-v1.2":
        order_id = _require_value(payload.get("order_ref"), "order_ref")
        customer = _require_mapping(payload.get("customer"), "customer")
        buyer = {
            "id": _require_value(customer.get("id"), "customer.id"),
            "displayName": _require_value(customer.get("name"), "customer.name"),
        }
        raw_items = payload.get("lines")
        items_path = "lines"
        ship_to = _require_mapping(payload.get("shipTo"), "shipTo")
        postal = ship_to.get("postal_code")
    else:
        order_id = _require_value(payload.get("id"), "id")
        buyer = {
            "id": _require_value(payload.get("customer_id"), "customer_id"),
            "displayName": _require_value(payload.get("customer_name"), "customer_name"),
        }
        raw_items = payload.get("items")
        items_path = "items"
        ship_to = _require_mapping(payload.get("ship_to"), "ship_to")
        postal = ship_to.get("postal")
        if postal is None:
            postal = ship_to.get("postalCode")

    if not isinstance(raw_items, list) or not raw_items:
        raise ConversionError(items_path, "missing line items")

    line_items = [
        _convert_line_item(item, f"{items_path}[{item_index}]")
        for item_index, item in enumerate(raw_items)
    ]

    address = {
        "country": _require_value(ship_to.get("country"), f"{items_path == 'lines' and 'shipTo' or 'ship_to'}.country"),
        "postalCode": _require_value(postal, f"{items_path == 'lines' and 'shipTo' or 'ship_to'}.postalCode"),
    }
    if source == "legacy-v1.2":
        shipping_method = payload.get("shipping_method")
        known_keys = {"order_ref", "customer", "lines", "shipTo", "shipping_method"}
    elif source == "legacy-v1.1":
        shipping_method = payload.get("shipping_method", payload.get("shipping"))
        known_keys = {"id", "customer_id", "customer_name", "items", "ship_to", "shipping_method", "shipping"}
    else:
        shipping_method = payload.get("shipping_method")
        known_keys = {"id", "customer_id", "customer_name", "items", "ship_to", "shipping_method"}

    unknown_fields = _extract_unknown_fields(payload, known_keys, stats, warnings, index=index)
    metadata = {"source": source}
    if unknown_fields:
        metadata["unknownFields"] = unknown_fields

    return {
        "orderId": order_id,
        "buyer": buyer,
        "lineItems": line_items,
        "shipping": {
            "method": _normalize_shipping_method(shipping_method),
            "address": address,
        },
        "metadata": metadata,
    }


def _convert_v2(payload, stats, warnings, index=None):
    order_id = _require_value(payload.get("orderId"), "orderId")
    buyer = _require_mapping(payload.get("buyer"), "buyer")
    shipping = _require_mapping(payload.get("shipping"), "shipping")
    address = _require_mapping(shipping.get("address"), "shipping.address")
    metadata = _require_mapping(payload.get("metadata"), "metadata")
    raw_items = payload.get("lineItems")

    if not isinstance(raw_items, list) or not raw_items:
        raise ConversionError("lineItems", "missing line items")

    converted_items = [
        _convert_line_item(item, f"lineItems[{item_index}]", legacy=False)
        for item_index, item in enumerate(raw_items)
    ]

    unknown_fields = deepcopy(metadata.get("unknownFields", {}))
    if not isinstance(unknown_fields, dict):
        raise ConversionError("metadata.unknownFields", "expected object")

    for key, value in metadata.items():
        if key in {"source", "unknownFields"}:
            continue
        unknown_fields[key] = deepcopy(value)
        stats["unknown_fields_count"] += 1

    result = {
        "orderId": order_id,
        "buyer": {
            "id": _require_value(buyer.get("id"), "buyer.id"),
            "displayName": _require_value(buyer.get("displayName"), "buyer.displayName"),
        },
        "lineItems": converted_items,
        "shipping": {
            "method": _normalize_shipping_method(shipping.get("method")),
            "address": {
                "country": _require_value(address.get("country"), "shipping.address.country"),
                "postalCode": _require_value(address.get("postalCode"), "shipping.address.postalCode"),
            },
        },
        "metadata": {"source": _require_value(metadata.get("source"), "metadata.source")},
    }
    if unknown_fields:
        result["metadata"]["unknownFields"] = unknown_fields
    return result


def convert_order(payload):
    """Convert supported legacy or v2 order payloads to the v2 public API shape."""
    payload = _require_mapping(payload, "payload")
    stats = {
        "pii_dropped_count": 0,
        "unknown_fields_count": 0,
    }
    warnings = []
    source = _detect_source(payload)
    if source == "public-v2":
        return _convert_v2(payload, stats, warnings)
    return _convert_legacy(payload, source, stats, warnings)


def _write_audit(audit):
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
            source = _detect_source(_require_mapping(payload, "payload"))
            if source == "public-v2":
                converted_payload = _convert_v2(payload, stats, warnings, index=index)
            else:
                converted_payload = _convert_legacy(payload, source, stats, warnings, index=index)
            converted.append(converted_payload)
            stats["converted_count"] += 1
        except ConversionError as exc:
            errors.append({
                "index": index,
                "path": exc.path,
                "error": exc.error,
            })
            stats["error_count"] += 1

    stats["warning_count"] = len(warnings)
    _write_audit(stats)
    return ConversionResult(converted, errors, warnings)


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
                raise ValueError(f"invalid JSON on line {line_number}: {exc.msg}") from exc
    return payloads


def main(argv=None):
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        raise SystemExit("usage: python -m client input.jsonl output.json")

    payloads = _load_jsonl(args[0])
    result = convert_many(payloads)
    with open(args[1], "w", encoding="utf-8") as handle:
        json.dump(result[0], handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result


if __name__ == "__main__":
    main()

import json
from copy import deepcopy
from pathlib import Path


PII_KEYS = {
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "phone_number",
    "passport_number",
}

V2_TOP_LEVEL_KEYS = {"orderId", "buyer", "lineItems", "shipping", "metadata"}
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

AUDIT_PATH = Path(__file__).with_name("conversion_audit.json")


class ConversionError(ValueError):
    def __init__(self, path, error):
        super().__init__(error)
        self.path = path
        self.error = error


class WarningCollector:
    def __init__(self, index=None):
        self.index = index
        self.warnings = []
        self.pii_dropped_count = 0
        self.unknown_fields_count = 0

    def add(self, path, warning):
        self.warnings.append({"index": self.index, "path": path, "warning": warning})

    def pii_drop(self, path):
        self.pii_dropped_count += 1
        self.add(path, "dropped pii-like field")

    def unknown_field(self, path):
        self.unknown_fields_count += 1
        self.add(path, "preserved unknown field")


def _is_blank(value):
    return value is None or (isinstance(value, str) and value.strip() == "")


def _require(payload, keys, path):
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    raise ConversionError(path, f"missing required field: {path}")


def _require_dict(payload, keys, path):
    value = _require(payload, keys, path)
    if not isinstance(value, dict):
        raise ConversionError(path, f"expected object at {path}")
    return value


def _require_list(payload, keys, path):
    value = _require(payload, keys, path)
    if not isinstance(value, list):
        raise ConversionError(path, f"expected array at {path}")
    return value


def _to_int(value, path):
    if isinstance(value, bool):
        raise ConversionError(path, f"expected integer at {path}")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ConversionError(path, f"expected integer at {path}")


def _shipping_method(payload, default_warning=None):
    method = payload.get("shipping_method")
    if method is None and "shipping" in payload and not isinstance(payload.get("shipping"), dict):
        method = payload.get("shipping")
    if _is_blank(method):
        if default_warning is not None:
            default_warning.add(default_warning_path(payload), 'defaulted blank shipping method to "standard"')
        return "standard"
    return method


def default_warning_path(payload):
    if "shipping_method" in payload:
        return "shipping_method"
    if "shipping" in payload and not isinstance(payload.get("shipping"), dict):
        return "shipping"
    return "shipping.method"


def _collect_unknown_fields(source, used_keys, collector, prefix=""):
    unknown = {}
    for key, value in source.items():
        if key in used_keys:
            continue
        path = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        if key in PII_KEYS:
            collector.pii_drop(path)
            continue
        unknown[key] = deepcopy(value)
        collector.unknown_field(path)
    return unknown


def _normalize_v2_line_items(line_items):
    if not isinstance(line_items, list):
        raise ConversionError("lineItems", "expected array at lineItems")
    normalized = []
    for i, item in enumerate(line_items):
        if not isinstance(item, dict):
            raise ConversionError(f"lineItems[{i}]", f"expected object at lineItems[{i}]")
        if "quantity" not in item:
            raise ConversionError(f"lineItems[{i}].quantity", f"missing required field: lineItems[{i}].quantity")
        if "unitPriceCents" not in item:
            raise ConversionError(f"lineItems[{i}].unitPriceCents", f"missing required field: lineItems[{i}].unitPriceCents")
        if isinstance(item.get("quantity"), int) and isinstance(item.get("unitPriceCents"), int):
            normalized.append(deepcopy(item))
            continue
        copy_item = deepcopy(item)
        copy_item["quantity"] = _to_int(item.get("quantity"), f"lineItems[{i}].quantity")
        copy_item["unitPriceCents"] = _to_int(item.get("unitPriceCents"), f"lineItems[{i}].unitPriceCents")
        normalized.append(copy_item)
    return normalized


def _normalize_legacy_lines(lines):
    normalized = []
    for i, item in enumerate(lines):
        if not isinstance(item, dict):
            raise ConversionError(f"items[{i}]", f"expected object at items[{i}]")
        sku = _require(item, ["sku"], f"items[{i}].sku")
        qty = _to_int(_require(item, ["qty"], f"items[{i}].qty"), f"items[{i}].qty")
        price = _to_int(
            _require(item, ["price_cents", "unit_price_cents"], f"items[{i}].price_cents"),
            f"items[{i}].price_cents" if "price_cents" in item else f"items[{i}].unit_price_cents",
        )
        normalized.append({"sku": sku, "quantity": qty, "unitPriceCents": price})
    return normalized


def _normalize_v2_metadata(metadata, collector):
    metadata = deepcopy(metadata or {})
    unknown_fields = metadata.get("unknownFields")
    if unknown_fields is None:
        unknown_fields = {}
    elif not isinstance(unknown_fields, dict):
        raise ConversionError("metadata.unknownFields", "expected object at metadata.unknownFields")
    else:
        unknown_fields = deepcopy(unknown_fields)
        collector.unknown_fields_count += len(unknown_fields)

    extra_metadata = {}
    for key in list(metadata.keys()):
        if key in {"source", "unknownFields"}:
            continue
        if key in PII_KEYS:
            collector.pii_drop(f"metadata.{key}")
        else:
            extra_metadata[key] = metadata[key]
            collector.unknown_field(f"metadata.{key}")
    if extra_metadata:
        unknown_fields.update(extra_metadata)
    metadata = {"source": metadata.get("source", "public-v2")}
    if unknown_fields:
        metadata["unknownFields"] = unknown_fields
    return metadata


def _convert_v2(payload, collector):
    order_id = _require(payload, ["orderId"], "orderId")
    buyer = _require_dict(payload, ["buyer"], "buyer")
    buyer_id = _require(buyer, ["id"], "buyer.id")
    buyer_name = _require(buyer, ["displayName"], "buyer.displayName")
    shipping = _require_dict(payload, ["shipping"], "shipping")
    address = _require_dict(shipping, ["address"], "shipping.address")
    postal = _require(address, ["postalCode"], "shipping.address.postalCode")
    country = _require(address, ["country"], "shipping.address.country")

    method = shipping.get("method")
    if _is_blank(method):
        collector.add("shipping.method", 'defaulted blank shipping method to "standard"')
        method = "standard"

    return {
        "orderId": order_id,
        "buyer": {"id": buyer_id, "displayName": buyer_name},
        "lineItems": _normalize_v2_line_items(_require_list(payload, ["lineItems"], "lineItems")),
        "shipping": {
            "method": method,
            "address": {"country": country, "postalCode": postal},
        },
        "metadata": _normalize_v2_metadata(payload.get("metadata"), collector),
    }


def _detect_legacy_version(payload):
    if "order_ref" in payload or "customer" in payload or "lines" in payload or "shipTo" in payload:
        return "legacy-v1.2"
    if "shipping" in payload and not isinstance(payload.get("shipping"), dict):
        return "legacy-v1.1"
    if isinstance(payload.get("ship_to"), dict) and "postalCode" in payload.get("ship_to", {}):
        return "legacy-v1.1"
    return "legacy-v1"


def _convert_legacy(payload, collector):
    version = _detect_legacy_version(payload)
    order_id = _require(payload, ["id", "order_ref"], "id")

    if "customer" in payload:
        customer = _require_dict(payload, ["customer"], "customer")
        buyer_id = _require(customer, ["id"], "customer.id")
        buyer_name = _require(customer, ["name"], "customer.name")
    else:
        buyer_id = _require(payload, ["customer_id"], "customer_id")
        buyer_name = _require(payload, ["customer_name"], "customer_name")

    lines = _require_list(payload, ["items", "lines"], "items")

    ship = _require_dict(payload, ["ship_to", "shipTo"], "ship_to")
    country = _require(ship, ["country"], "ship_to.country")
    postal = None
    postal_path = None
    for key, path in [
        ("postal", "ship_to.postal"),
        ("postalCode", "ship_to.postalCode"),
        ("postal_code", "shipTo.postal_code"),
    ]:
        if key in ship and ship[key] is not None:
            postal = ship[key]
            postal_path = path
            break
    if postal is None:
        raise ConversionError("ship_to.postal", "missing required field: ship_to.postal")

    metadata = {"source": version}
    used = {
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
    unknown_fields = _collect_unknown_fields(payload, used, collector)
    if unknown_fields:
        metadata["unknownFields"] = unknown_fields

    return {
        "orderId": order_id,
        "buyer": {"id": buyer_id, "displayName": buyer_name},
        "lineItems": _normalize_legacy_lines(lines),
        "shipping": {
            "method": _shipping_method(payload, collector),
            "address": {"country": country, "postalCode": postal},
        },
        "metadata": metadata,
    }


def convert_order(payload):
    """Convert legacy or v2 order payloads to the v2 public API shape."""
    if not isinstance(payload, dict):
        raise ConversionError("$", "payload must be an object")
    collector = WarningCollector(index=None)
    if "orderId" in payload and "buyer" in payload and "lineItems" in payload and "shipping" in payload:
        return _convert_v2(payload, collector)
    return _convert_legacy(payload, collector)


def convert_many(payloads):
    converted = []
    errors = []
    warnings = []
    pii_dropped_count = 0
    unknown_fields_count = 0

    for index, payload in enumerate(payloads):
        collector = WarningCollector(index=index)
        try:
            if not isinstance(payload, dict):
                raise ConversionError("$", "payload must be an object")
            if "orderId" in payload and "buyer" in payload and "lineItems" in payload and "shipping" in payload:
                converted.append(_convert_v2(payload, collector))
            else:
                converted.append(_convert_legacy(payload, collector))
        except ConversionError as exc:
            errors.append({"index": index, "path": exc.path, "error": exc.error})
        warnings.extend(collector.warnings)
        pii_dropped_count += collector.pii_dropped_count
        unknown_fields_count += collector.unknown_fields_count

    audit = {
        "converted_count": len(converted),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "pii_dropped_count": pii_dropped_count,
        "unknown_fields_count": unknown_fields_count,
    }
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")

    if warnings:
        return converted, errors, warnings
    return converted, errors


def summarize_order(v2_payload):
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def _read_jsonl(path):
    payloads = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payloads.append(json.loads(line))
    return payloads


def main(argv=None):
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        raise SystemExit("usage: python -m client input.jsonl output.json")

    payloads = _read_jsonl(argv[0])
    result = convert_many(payloads)
    converted = result[0]
    with open(argv[1], "w", encoding="utf-8") as handle:
        json.dump(converted, handle, indent=2)
    return result


if __name__ == "__main__":
    main()

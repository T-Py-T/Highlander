import json
import sys
from copy import deepcopy
from pathlib import Path


AUDIT_PATH = Path(__file__).with_name("conversion_audit.json")
PII_KEYS = {
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "phone_number",
    "passport_number",
}


class ConversionIssue(ValueError):
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


def _normalize_int(value, path):
    if isinstance(value, bool) or value is None:
        raise ConversionIssue(path, "Expected integer value")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConversionIssue(path, "Expected integer value") from exc


def _normalize_shipping_method(value, warnings):
    if value is None or (isinstance(value, str) and not value.strip()):
        warnings.append({"path": "shipping.method", "warning": "Defaulted blank shipping method to standard"})
        return "standard"
    return value


def _drop_pii(value, warnings, stats, path=""):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in PII_KEYS:
                stats["pii_dropped_count"] += 1
                warnings.append({"path": child_path, "warning": "Dropped PII field from unknownFields"})
                continue
            nested = _drop_pii(item, warnings, stats, child_path)
            if nested not in ({}, []):
                cleaned[key] = nested
        return cleaned
    if isinstance(value, list):
        cleaned = []
        for index, item in enumerate(value):
            nested = _drop_pii(item, warnings, stats, f"{path}[{index}]")
            if nested not in ({}, []):
                cleaned.append(nested)
        return cleaned
    return value


def _count_unknown_fields(value):
    if isinstance(value, dict):
        return sum(1 + _count_unknown_fields(item) for item in value.values())
    if isinstance(value, list):
        return sum(_count_unknown_fields(item) for item in value)
    return 0


def _set_unknown_field(unknown_fields, key, value):
    if value in ({}, []):
        return
    unknown_fields[key] = value


def _extract_legacy_unknown_fields(payload, warnings, stats):
    unknown_fields = {}
    top_level_mapped = {
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

    for key, value in payload.items():
        if key in top_level_mapped:
            continue
        if key in PII_KEYS:
            stats["pii_dropped_count"] += 1
            warnings.append({"path": key, "warning": "Dropped PII field from unknownFields"})
            continue
        _set_unknown_field(unknown_fields, key, _drop_pii(value, warnings, stats, key))

    customer = payload.get("customer")
    if isinstance(customer, dict):
        extra_customer = {}
        for key, value in customer.items():
            if key not in {"id", "name"}:
                if key in PII_KEYS:
                    stats["pii_dropped_count"] += 1
                    warnings.append({"path": f"customer.{key}", "warning": "Dropped PII field from unknownFields"})
                    continue
                _set_unknown_field(extra_customer, key, _drop_pii(value, warnings, stats, f"customer.{key}"))
        if extra_customer:
            unknown_fields["customer"] = extra_customer

    ship_to = payload.get("ship_to")
    if isinstance(ship_to, dict):
        extra_ship_to = {}
        for key, value in ship_to.items():
            if key not in {"country", "postal", "postalCode"}:
                if key in PII_KEYS:
                    stats["pii_dropped_count"] += 1
                    warnings.append({"path": f"ship_to.{key}", "warning": "Dropped PII field from unknownFields"})
                    continue
                _set_unknown_field(extra_ship_to, key, _drop_pii(value, warnings, stats, f"ship_to.{key}"))
        if extra_ship_to:
            unknown_fields["ship_to"] = extra_ship_to

    ship_to_v12 = payload.get("shipTo")
    if isinstance(ship_to_v12, dict):
        extra_ship_to_v12 = {}
        for key, value in ship_to_v12.items():
            if key not in {"country", "postal_code"}:
                if key in PII_KEYS:
                    stats["pii_dropped_count"] += 1
                    warnings.append({"path": f"shipTo.{key}", "warning": "Dropped PII field from unknownFields"})
                    continue
                _set_unknown_field(extra_ship_to_v12, key, _drop_pii(value, warnings, stats, f"shipTo.{key}"))
        if extra_ship_to_v12:
            unknown_fields["shipTo"] = extra_ship_to_v12

    return unknown_fields


def _convert_legacy_line_items(items, path_prefix):
    if not isinstance(items, list) or not items:
        raise ConversionIssue(path_prefix, "Missing or empty line items")

    line_items = []
    for index, item in enumerate(items):
        item_path = f"{path_prefix}[{index}]"
        if not isinstance(item, dict):
            raise ConversionIssue(item_path, "Line item must be an object")
        if "sku" not in item:
            raise ConversionIssue(f"{item_path}.sku", "Missing sku")
        qty_path = f"{item_path}.qty"
        price_key = "price_cents" if "price_cents" in item else "unit_price_cents"
        if price_key not in item:
            raise ConversionIssue(f"{item_path}.price_cents", "Missing price_cents")
        line_items.append(
            {
                "sku": item["sku"],
                "quantity": _normalize_int(item.get("qty"), qty_path),
                "unitPriceCents": _normalize_int(item.get(price_key), f"{item_path}.{price_key}"),
            }
        )
    return line_items


def _require_string(value, path):
    if value is None or value == "":
        raise ConversionIssue(path, f"Missing required field at {path}")
    return value


def _convert_legacy(payload, source):
    warnings = []
    stats = {"pii_dropped_count": 0, "unknown_fields_count": 0}

    if source == "legacy-v1.2":
        order_id = _require_string(payload.get("order_ref"), "order_ref")
        customer = payload.get("customer")
        if not isinstance(customer, dict):
            raise ConversionIssue("customer", "Missing required customer object")
        buyer_id = _require_string(customer.get("id"), "customer.id")
        display_name = _require_string(customer.get("name"), "customer.name")
        line_items = _convert_legacy_line_items(payload.get("lines"), "lines")
        shipping_source = payload.get("shipTo")
        shipping_path = "shipTo"
        postal_keys = ["postal_code"]
    else:
        order_id = _require_string(payload.get("id"), "id")
        buyer_id = _require_string(payload.get("customer_id"), "customer_id")
        display_name = _require_string(payload.get("customer_name"), "customer_name")
        line_items = _convert_legacy_line_items(payload.get("items"), "items")
        shipping_source = payload.get("ship_to")
        shipping_path = "ship_to"
        postal_keys = ["postal", "postalCode"]

    if not isinstance(shipping_source, dict):
        raise ConversionIssue(shipping_path, f"Missing required field at {shipping_path}")

    country = _require_string(shipping_source.get("country"), f"{shipping_path}.country")
    postal_code = None
    postal_path = None
    for key in postal_keys:
        if shipping_source.get(key) not in (None, ""):
            postal_code = shipping_source[key]
            postal_path = f"{shipping_path}.{key}"
            break
    if postal_code is None:
        missing_key = postal_keys[0]
        raise ConversionIssue(f"{shipping_path}.{missing_key}", f"Missing required field at {shipping_path}.{missing_key}")

    shipping_method = payload.get("shipping_method")
    if source == "legacy-v1.1" and "shipping" in payload:
        shipping_method = payload.get("shipping")

    unknown_fields = _extract_legacy_unknown_fields(payload, warnings, stats)
    stats["unknown_fields_count"] = _count_unknown_fields(unknown_fields)

    return {
        "payload": {
            "orderId": order_id,
            "buyer": {"id": buyer_id, "displayName": display_name},
            "lineItems": line_items,
            "shipping": {
                "method": _normalize_shipping_method(shipping_method, warnings),
                "address": {"country": country, "postalCode": postal_code},
            },
            "metadata": _legacy_metadata(source, unknown_fields),
        },
        "warnings": warnings,
        "stats": stats,
    }


def _legacy_metadata(source, unknown_fields):
    metadata = {"source": source}
    if unknown_fields:
        metadata["unknownFields"] = unknown_fields
    return metadata


def _convert_v2(payload):
    warnings = []
    stats = {"pii_dropped_count": 0, "unknown_fields_count": 0}
    migrated = deepcopy(payload)

    order_id = _require_string(migrated.get("orderId"), "orderId")
    buyer = migrated.get("buyer")
    if not isinstance(buyer, dict):
        raise ConversionIssue("buyer", "Missing required buyer object")
    _require_string(buyer.get("id"), "buyer.id")
    _require_string(buyer.get("displayName"), "buyer.displayName")

    line_items = migrated.get("lineItems")
    if not isinstance(line_items, list) or not line_items:
        raise ConversionIssue("lineItems", "Missing or empty lineItems")

    shipping = migrated.get("shipping")
    if not isinstance(shipping, dict):
        raise ConversionIssue("shipping", "Missing required shipping object")
    address = shipping.get("address")
    if not isinstance(address, dict):
        raise ConversionIssue("shipping.address", "Missing required shipping.address object")
    _require_string(address.get("country"), "shipping.address.country")
    _require_string(address.get("postalCode"), "shipping.address.postalCode")
    shipping["method"] = _normalize_shipping_method(shipping.get("method"), warnings)

    metadata = migrated.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        migrated["metadata"] = metadata
    metadata["source"] = metadata.get("source") or "public-v2"

    unknown_fields = metadata.get("unknownFields")
    if unknown_fields is None:
        unknown_fields = {}
    elif not isinstance(unknown_fields, dict):
        raise ConversionIssue("metadata.unknownFields", "metadata.unknownFields must be an object")

    extra_metadata = {}
    for key in list(metadata.keys()):
        if key in {"source", "unknownFields"}:
            continue
        extra_metadata[key] = metadata.pop(key)

    merged_unknown = dict(unknown_fields)
    for key, value in extra_metadata.items():
        if key in PII_KEYS:
            stats["pii_dropped_count"] += 1
            warnings.append({"path": f"metadata.{key}", "warning": "Dropped PII field from unknownFields"})
            continue
        cleaned = _drop_pii(value, warnings, stats, f"metadata.{key}")
        if cleaned not in ({}, []):
            merged_unknown[key] = cleaned
    if merged_unknown:
        metadata["unknownFields"] = merged_unknown
    elif "unknownFields" in metadata:
        metadata["unknownFields"] = merged_unknown

    stats["unknown_fields_count"] = _count_unknown_fields(metadata.get("unknownFields", {}))

    return {
        "payload": migrated,
        "warnings": warnings,
        "stats": stats,
    }


def convert_order(payload):
    """Convert a legacy or v2 order payload to the v2 public API shape."""
    if not isinstance(payload, dict):
        raise ConversionIssue("$", "Payload must be an object")

    if "orderId" in payload:
        return _convert_v2(payload)["payload"]
    if "order_ref" in payload or "customer" in payload or "lines" in payload or "shipTo" in payload:
        return _convert_legacy(payload, "legacy-v1.2")["payload"]
    source = "legacy-v1.1" if "shipping" in payload or payload.get("ship_to", {}).get("postalCode") else "legacy-v1"
    return _convert_legacy(payload, source)["payload"]


def convert_many(payloads):
    converted = []
    errors = []
    warnings = []
    audit = {
        "converted_count": 0,
        "error_count": 0,
        "warning_count": 0,
        "pii_dropped_count": 0,
        "unknown_fields_count": 0,
    }

    for index, payload in enumerate(payloads):
        try:
            if not isinstance(payload, dict):
                raise ConversionIssue("$", "Payload must be an object")
            if "orderId" in payload:
                result = _convert_v2(payload)
            elif "order_ref" in payload or "customer" in payload or "lines" in payload or "shipTo" in payload:
                result = _convert_legacy(payload, "legacy-v1.2")
            else:
                source = "legacy-v1.1" if "shipping" in payload or payload.get("ship_to", {}).get("postalCode") else "legacy-v1"
                result = _convert_legacy(payload, source)
            converted.append(result["payload"])
            audit["converted_count"] += 1
            audit["pii_dropped_count"] += result["stats"]["pii_dropped_count"]
            audit["unknown_fields_count"] += result["stats"]["unknown_fields_count"]
            for warning in result["warnings"]:
                warnings.append({"index": index, **warning})
        except ConversionIssue as exc:
            errors.append({"index": index, "path": exc.path, "error": exc.error})

    audit["error_count"] = len(errors)
    audit["warning_count"] = len(warnings)
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
                raise ConversionIssue(f"input[{line_number}]", f"Invalid JSON: {exc.msg}") from exc
    return payloads


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        raise SystemExit("Usage: python -m client input.jsonl output.json")

    payloads = _load_jsonl(argv[0])
    result = convert_many(payloads)
    with open(argv[1], "w", encoding="utf-8") as handle:
        json.dump(result[0], handle, indent=2)
        handle.write("\n")
    return 0 if not result[1] else 1


if __name__ == "__main__":
    raise SystemExit(main())

import copy
import json
import sys
from pathlib import Path


AUDIT_PATH = Path(__file__).with_name("conversion_audit.json")
SENSITIVE_KEYS = {
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "phone_number",
    "passport_number",
}


def _normalize_key(value):
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


NORMALIZED_SENSITIVE_KEYS = {_normalize_key(item) for item in SENSITIVE_KEYS}


def _is_sensitive_key(key):
    normalized = _normalize_key(key)
    return normalized in NORMALIZED_SENSITIVE_KEYS


def _is_blank(value):
    return value is None or (isinstance(value, str) and value.strip() == "")


def _require(mapping, key, path):
    if key not in mapping or mapping[key] is None:
        raise ValueError(f"missing required field: {path}")
    return mapping[key]


def _coerce_int(value, path):
    if isinstance(value, bool):
        raise ValueError(f"invalid integer at {path}")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid integer at {path}")


def _extract_unknowns(value, stats, base_path=""):
    if isinstance(value, dict):
        kept = {}
        for key, item in value.items():
            path = f"{base_path}.{key}" if base_path else str(key)
            if _is_sensitive_key(key):
                stats["pii_dropped_count"] += 1
                stats["warnings"].append({"path": path, "warning": "dropped sensitive field"})
                continue
            cleaned = _extract_unknowns(item, stats, path)
            kept[key] = cleaned
            stats["unknown_fields_count"] += 1
        return kept
    if isinstance(value, list):
        kept_list = []
        for index, item in enumerate(value):
            path = f"{base_path}[{index}]" if base_path else f"[{index}]"
            kept_list.append(_extract_unknowns(item, stats, path))
        return kept_list
    return value


def _detect_version(payload):
    if all(key in payload for key in ("orderId", "buyer", "lineItems", "shipping", "metadata")):
        return "public-v2"
    if any(key in payload for key in ("order_ref", "customer", "lines", "shipTo")):
        return "legacy-v1.2"
    if "shipping" in payload or (isinstance(payload.get("ship_to"), dict) and "postalCode" in payload["ship_to"]):
        return "legacy-v1.1"
    return "legacy-v1"


def _convert_legacy_line_items(items, field_name):
    if not isinstance(items, list):
        raise ValueError(f"invalid array at {field_name}")

    converted = []
    extras = []
    for index, item in enumerate(items):
        path = f"{field_name}[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"invalid object at {path}")
        converted.append(
            {
                "sku": _require(item, "sku", f"{path}.sku"),
                "quantity": _coerce_int(_require(item, "qty", f"{path}.qty"), f"{path}.qty"),
                "unitPriceCents": _coerce_int(
                    _require(
                        item,
                        "unit_price_cents" if "unit_price_cents" in item else "price_cents",
                        f"{path}.price_cents",
                    ),
                    f"{path}.{'unit_price_cents' if 'unit_price_cents' in item else 'price_cents'}",
                ),
            }
        )
        extra = {
            key: value
            for key, value in item.items()
            if key not in {"sku", "qty", "price_cents", "unit_price_cents"}
        }
        if extra:
            extras.append(extra)
        else:
            extras.append(None)
    return converted, extras


def _legacy_unknown_fields(payload, version, line_item_extras, stats):
    known = {
        "legacy-v1": {"id", "customer_id", "customer_name", "items", "ship_to", "shipping_method"},
        "legacy-v1.1": {"id", "customer_id", "customer_name", "items", "ship_to", "shipping_method", "shipping"},
        "legacy-v1.2": {"order_ref", "customer", "lines", "shipTo", "shipping_method", "shipping"},
    }[version]
    unknown = {key: value for key, value in payload.items() if key not in known}

    if version == "legacy-v1.2" and isinstance(payload.get("customer"), dict):
        customer_extra = {key: value for key, value in payload["customer"].items() if key not in {"id", "name"}}
        if customer_extra:
            unknown["customer"] = customer_extra

    ship_key = "shipTo" if version == "legacy-v1.2" else "ship_to"
    postal_keys = {"country", "postal", "postalCode", "postal_code"}
    if isinstance(payload.get(ship_key), dict):
        shipping_extra = {key: value for key, value in payload[ship_key].items() if key not in postal_keys}
        if shipping_extra:
            unknown[ship_key] = shipping_extra

    if any(extra is not None for extra in line_item_extras):
        unknown["lines" if version == "legacy-v1.2" else "items"] = line_item_extras

    cleaned = _extract_unknowns(unknown, stats)
    if cleaned:
        return cleaned
    return None


def _convert_legacy(payload):
    stats = {"pii_dropped_count": 0, "unknown_fields_count": 0, "warnings": []}
    version = _detect_version(payload)

    if version == "legacy-v1.2":
        order_id = _require(payload, "order_ref", "order_ref")
        customer = _require(payload, "customer", "customer")
        if not isinstance(customer, dict):
            raise ValueError("invalid object at customer")
        buyer_id = _require(customer, "id", "customer.id")
        display_name = _require(customer, "name", "customer.name")
        items = _require(payload, "lines", "lines")
        shipping_source = _require(payload, "shipTo", "shipTo")
        item_field = "lines"
    else:
        order_id = _require(payload, "id", "id")
        buyer_id = _require(payload, "customer_id", "customer_id")
        display_name = _require(payload, "customer_name", "customer_name")
        items = _require(payload, "items", "items")
        shipping_source = _require(payload, "ship_to", "ship_to")
        item_field = "items"

    if not isinstance(shipping_source, dict):
        raise ValueError(f"invalid object at {'shipTo' if version == 'legacy-v1.2' else 'ship_to'}")

    line_items, line_item_extras = _convert_legacy_line_items(items, item_field)
    postal = (
        shipping_source.get("postal_code")
        if version == "legacy-v1.2"
        else shipping_source.get("postalCode", shipping_source.get("postal"))
    )
    if postal is None:
        raise ValueError("missing required field: shipTo.postal_code" if version == "legacy-v1.2" else "missing required field: ship_to.postal")

    shipping_method = payload.get("shipping_method", payload.get("shipping"))
    if _is_blank(shipping_method):
        shipping_method = "standard"
        stats["warnings"].append({"path": "shipping_method", "warning": "defaulted blank shipping method to standard"})

    converted = {
        "orderId": str(order_id),
        "buyer": {"id": str(buyer_id), "displayName": str(display_name)},
        "lineItems": line_items,
        "shipping": {
            "method": shipping_method,
            "address": {
                "country": _require(shipping_source, "country", f"{'shipTo' if version == 'legacy-v1.2' else 'ship_to'}.country"),
                "postalCode": str(postal),
            },
        },
        "metadata": {"source": version},
    }

    unknown_fields = _legacy_unknown_fields(payload, version, line_item_extras, stats)
    if unknown_fields:
        converted["metadata"]["unknownFields"] = unknown_fields
    return converted, stats


def _convert_v2(payload):
    stats = {"pii_dropped_count": 0, "unknown_fields_count": 0, "warnings": []}
    converted = copy.deepcopy(payload)

    shipping = _require(converted, "shipping", "shipping")
    if not isinstance(shipping, dict):
        raise ValueError("invalid object at shipping")
    address = _require(shipping, "address", "shipping.address")
    if not isinstance(address, dict):
        raise ValueError("invalid object at shipping.address")

    _require(converted, "orderId", "orderId")
    buyer = _require(converted, "buyer", "buyer")
    if not isinstance(buyer, dict):
        raise ValueError("invalid object at buyer")
    _require(buyer, "id", "buyer.id")
    _require(buyer, "displayName", "buyer.displayName")
    line_items = _require(converted, "lineItems", "lineItems")
    if not isinstance(line_items, list):
        raise ValueError("invalid array at lineItems")

    for index, item in enumerate(line_items):
        if not isinstance(item, dict):
            raise ValueError(f"invalid object at lineItems[{index}]")
        _require(item, "sku", f"lineItems[{index}].sku")
        _require(item, "quantity", f"lineItems[{index}].quantity")
        _require(item, "unitPriceCents", f"lineItems[{index}].unitPriceCents")

    _require(address, "country", "shipping.address.country")
    _require(address, "postalCode", "shipping.address.postalCode")

    metadata = _require(converted, "metadata", "metadata")
    if not isinstance(metadata, dict):
        raise ValueError("invalid object at metadata")
    _require(metadata, "source", "metadata.source")

    unknown_fields = metadata.get("unknownFields")
    if unknown_fields is None:
        unknown_fields = {}
    elif not isinstance(unknown_fields, dict):
        raise ValueError("invalid object at metadata.unknownFields")

    extra_metadata = {key: value for key, value in metadata.items() if key not in {"source", "unknownFields"}}
    if extra_metadata:
        cleaned = _extract_unknowns(extra_metadata, stats, "metadata")
        if cleaned:
            unknown_fields.update(cleaned)
        for key in extra_metadata:
            metadata.pop(key, None)
    if unknown_fields:
        metadata["unknownFields"] = unknown_fields

    if _is_blank(shipping.get("method")):
        shipping["method"] = "standard"
        stats["warnings"].append({"path": "shipping.method", "warning": "defaulted blank shipping method to standard"})

    return converted, stats


def convert_order(payload):
    """Convert a legacy or v2 order payload to the v2 public API shape."""
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    version = _detect_version(payload)
    converted, _stats = _convert_v2(payload) if version == "public-v2" else _convert_legacy(payload)
    return converted


def _write_audit(audit):
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")


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
            version = _detect_version(payload) if isinstance(payload, dict) else None
            item, stats = _convert_v2(payload) if version == "public-v2" else _convert_legacy(payload)
            converted.append(item)
            audit["converted_count"] += 1
            audit["pii_dropped_count"] += stats["pii_dropped_count"]
            audit["unknown_fields_count"] += stats["unknown_fields_count"]
            for warning in stats["warnings"]:
                warnings.append({"index": index, **warning})
        except Exception as exc:
            message = str(exc)
            path = "payload"
            if ": " in message:
                path = message.split(": ", 1)[1]
            elif " at " in message:
                path = message.rsplit(" at ", 1)[1]
            errors.append({"index": index, "path": path, "error": message})

    audit["error_count"] = len(errors)
    audit["warning_count"] = len(warnings)
    _write_audit(audit)
    if warnings:
        return converted, errors, warnings
    return converted, errors


def summarize_order(v2_payload):
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def _read_jsonl(path):
    payloads = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                payloads.append(json.loads(stripped))
    return payloads


def _main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: python -m client input.jsonl output.json")

    payloads = _read_jsonl(argv[1])
    result = convert_many(payloads)
    converted = result[0]
    output_path = Path(argv[2])
    output_path.write_text(json.dumps(converted, indent=2), encoding="utf-8")


if __name__ == "__main__":
    _main(sys.argv)

"""Conversion helpers for the legacy order API migration."""

import copy
import json
import sys
from pathlib import Path


_PII_KEYS = {
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "phone_number",
    "passport_number",
}
_KNOWN_LEGACY_FIELDS = {
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
    """An input error with a useful payload-relative path."""

    def __init__(self, path, message):
        self.path = path
        super().__init__(message)


def _required_mapping(payload, path="payload"):
    if not isinstance(payload, dict):
        raise ConversionError(path, "payload must be an object")
    return payload


def _required(payload, key, path="payload"):
    value = payload.get(key)
    if value is None or value == "":
        raise ConversionError(f"{path}.{key}", f"missing required field: {key}")
    return value


def _integer(value, path):
    # bool is an int subclass but is not a meaningful quantity or price.
    if isinstance(value, bool):
        raise ConversionError(path, "must be an integer")
    try:
        converted = int(value)
    except (TypeError, ValueError):
        raise ConversionError(path, "must be an integer") from None
    if isinstance(value, float) and value != converted:
        raise ConversionError(path, "must be an integer")
    if isinstance(value, str) and str(converted) != value.strip():
        raise ConversionError(path, "must be an integer")
    return converted


def _sanitize_unknown(value, path, audit):
    if isinstance(value, dict):
        result = {}
        for key, nested in value.items():
            if str(key).lower() in _PII_KEYS:
                audit["pii_dropped_count"] += 1
                continue
            result[key] = _sanitize_unknown(nested, f"{path}.{key}", audit)
        return result
    if isinstance(value, list):
        return [_sanitize_unknown(item, path, audit) for item in value]
    return copy.deepcopy(value)


def _legacy_unknown_fields(payload, audit):
    unknown = {}
    for key, value in payload.items():
        if key in _KNOWN_LEGACY_FIELDS:
            continue
        if str(key).lower() in _PII_KEYS:
            audit["pii_dropped_count"] += 1
            continue
        unknown[key] = _sanitize_unknown(value, f"metadata.unknownFields.{key}", audit)
    audit["unknown_fields_count"] += len(unknown)
    return unknown


def _convert_legacy(payload, audit):
    order_id = payload.get("id", payload.get("order_ref"))
    if order_id is None or order_id == "":
        raise ConversionError("orderId", "missing required field: id or order_ref")

    customer = payload.get("customer")
    if customer is not None and not isinstance(customer, dict):
        raise ConversionError("customer", "must be an object")
    customer_id = payload.get("customer_id")
    if customer_id is None and customer:
        customer_id = customer.get("id")
    customer_name = payload.get("customer_name")
    if customer_name is None and customer:
        customer_name = customer.get("name")
    if customer_id is None or customer_id == "":
        raise ConversionError("customer_id", "missing required customer id")
    if customer_name is None or customer_name == "":
        raise ConversionError("customer_name", "missing required customer name")

    source_items = payload.get("items", payload.get("lines"))
    if not isinstance(source_items, list):
        raise ConversionError("items", "missing required items/lines array")
    line_items = []
    for index, item in enumerate(source_items):
        path = f"items[{index}]"
        if not isinstance(item, dict):
            raise ConversionError(path, "line item must be an object")
        if "sku" not in item or item["sku"] in (None, ""):
            raise ConversionError(f"{path}.sku", "missing required field: sku")
        qty = item.get("qty")
        price = item.get("price_cents", item.get("unit_price_cents"))
        if qty is None:
            raise ConversionError(f"{path}.qty", "missing required field: qty")
        if price is None:
            raise ConversionError(f"{path}.price_cents", "missing required price")
        line_items.append({
            "sku": item["sku"],
            "quantity": _integer(qty, f"{path}.qty"),
            "unitPriceCents": _integer(price, f"{path}.price_cents"),
        })

    address = payload.get("ship_to", payload.get("shipTo"))
    if not isinstance(address, dict):
        raise ConversionError("ship_to", "missing required shipping address")
    postal = address.get("postal", address.get("postalCode", address.get("postal_code")))
    if postal is None or postal == "":
        raise ConversionError("ship_to.postal", "missing required postal code")
    shipping_method = payload.get("shipping_method", payload.get("shipping"))
    if shipping_method is None or (isinstance(shipping_method, str) and not shipping_method.strip()):
        shipping_method = "standard"

    unknown = _legacy_unknown_fields(payload, audit)
    metadata = {"source": "legacy-v1"}
    if unknown:
        metadata["unknownFields"] = unknown
    return {
        "orderId": order_id,
        "buyer": {"id": customer_id, "displayName": customer_name},
        "lineItems": line_items,
        "shipping": {
            "method": shipping_method,
            "address": {"country": address.get("country"), "postalCode": postal},
        },
        "metadata": metadata,
    }


def _convert_v2(payload, audit=None):
    result = copy.deepcopy(payload)
    shipping = result.get("shipping")
    if isinstance(shipping, dict) and (shipping.get("method") is None or
                                       (isinstance(shipping.get("method"), str) and not shipping["method"].strip())):
        shipping["method"] = "standard"
    metadata = result.get("metadata")
    if isinstance(metadata, dict):
        extra = {key: value for key, value in metadata.items()
                 if key not in {"source", "unknownFields"}}
        if extra:
            unknown = metadata.setdefault("unknownFields", {})
            if isinstance(unknown, dict):
                unknown.update(extra)
                for key in extra:
                    metadata.pop(key, None)
        if audit is not None and isinstance(metadata.get("unknownFields"), dict):
            audit["unknown_fields_count"] += len(metadata["unknownFields"])
    return result


def convert_order(payload):
    """Convert a legacy order, or normalize an already-public v2 order."""
    payload = _required_mapping(payload)
    if "orderId" in payload or "lineItems" in payload:
        return _convert_v2(payload)
    return _convert_legacy(payload, {"pii_dropped_count": 0, "unknown_fields_count": 0})


def summarize_order(v2_payload):
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def convert_many(payloads):
    converted, errors, warnings = [], [], []
    audit = {"converted_count": 0, "error_count": 0, "warning_count": 0,
             "pii_dropped_count": 0, "unknown_fields_count": 0}
    for index, payload in enumerate(payloads):
        try:
            local_audit = {"pii_dropped_count": 0, "unknown_fields_count": 0}
            if isinstance(payload, dict) and ("orderId" in payload or "lineItems" in payload):
                converted.append(_convert_v2(payload, local_audit))
            else:
                converted.append(_convert_legacy(payload, local_audit))
            audit["converted_count"] += 1
            audit["pii_dropped_count"] += local_audit["pii_dropped_count"]
            audit["unknown_fields_count"] += local_audit["unknown_fields_count"]
        except ConversionError as exc:
            errors.append({"index": index, "path": exc.path, "error": str(exc)})
        except (TypeError, ValueError, KeyError) as exc:
            errors.append({"index": index, "path": "payload", "error": str(exc)})
    audit["error_count"] = len(errors)
    audit["warning_count"] = len(warnings)
    Path(__file__).with_name("conversion_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return (converted, errors, warnings) if warnings else (converted, errors)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        raise SystemExit("usage: python -m client input.jsonl output.json")
    input_path, output_path = map(Path, argv)
    payloads = [json.loads(line) for line in input_path.read_text().splitlines() if line.strip()]
    result = convert_many(payloads)
    Path(output_path).write_text(json.dumps(result[0], indent=2) + "\n")


if __name__ == "__main__":
    main()

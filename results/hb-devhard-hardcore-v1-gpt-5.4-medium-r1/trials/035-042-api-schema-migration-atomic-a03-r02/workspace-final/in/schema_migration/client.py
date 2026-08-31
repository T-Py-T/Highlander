from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Iterable

AUDIT_PATH = Path(__file__).with_name("conversion_audit.json")
PII_KEYS = {
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "phone_number",
    "passport_number",
}


class ConversionError(ValueError):
    def __init__(self, path: str, error: str):
        super().__init__(error)
        self.path = path
        self.error = error


class AuditTracker:
    def __init__(self) -> None:
        self.pii_dropped_count = 0
        self.unknown_fields_count = 0


class WarningTracker:
    def __init__(self, index: int) -> None:
        self.index = index
        self.warnings: list[dict[str, Any]] = []

    def add(self, path: str, warning: str) -> None:
        self.warnings.append({"index": self.index, "path": path, "warning": warning})


def _raise(path: str, error: str) -> None:
    raise ConversionError(path, error)


def _require_mapping(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        _raise("$", "payload must be an object")
    return payload


def _require_value(value: Any, path: str) -> Any:
    if value is None or (isinstance(value, str) and not value.strip()):
        _raise(path, f"missing required field: {path}")
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        _raise(path, f"{path} must be a list")
    return value


def _require_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _raise(path, f"{path} must be an object")
    return value


def _to_int(value: Any, path: str) -> int:
    if isinstance(value, bool):
        _raise(path, f"{path} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            pass
    _raise(path, f"{path} must be an integer")


def _shipping_method(value: Any) -> str:
    if value is None:
        return "standard"
    if isinstance(value, str) and not value.strip():
        return "standard"
    return str(value)


def _payload_version(payload: dict[str, Any]) -> str:
    if {"orderId", "buyer", "lineItems", "shipping"}.issubset(payload.keys()):
        return "public-v2"
    if any(key in payload for key in ("order_ref", "customer", "lines", "shipTo")):
        return "legacy-v1.2"
    if "shipping" in payload:
        return "legacy-v1.1"
    ship_to = payload.get("ship_to")
    if isinstance(ship_to, dict) and "postalCode" in ship_to:
        return "legacy-v1.1"
    return "legacy-v1"


def _split_unknown_fields(
    values: dict[str, Any],
    *,
    audit: AuditTracker | None,
    warnings: WarningTracker | None,
    base_path: str,
) -> dict[str, Any]:
    kept: dict[str, Any] = {}
    for key, value in values.items():
        path = f"{base_path}.{key}" if base_path else key
        if key in PII_KEYS:
            if audit is not None:
                audit.pii_dropped_count += 1
            if warnings is not None:
                warnings.add(path, "dropped PII-like field")
            continue
        kept[key] = copy.deepcopy(value)
        if audit is not None:
            audit.unknown_fields_count += 1
        if warnings is not None:
            warnings.add(path, "preserved unknown field")
    return kept


def _convert_legacy_lines(lines: Any, source_path: str) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(_require_list(lines, source_path)):
        item_path = f"{source_path}[{index}]"
        item = _require_dict(item, item_path)
        sku = _require_value(item.get("sku"), f"{item_path}.sku")
        qty = _to_int(item.get("qty"), f"{item_path}.qty")
        if "price_cents" in item:
            unit_price = _to_int(item.get("price_cents"), f"{item_path}.price_cents")
        elif "unit_price_cents" in item:
            unit_price = _to_int(item.get("unit_price_cents"), f"{item_path}.unit_price_cents")
        else:
            _raise(f"{item_path}.price_cents", f"missing required field: {item_path}.price_cents")
        result.append({"sku": sku, "quantity": qty, "unitPriceCents": unit_price})
    return result


def _convert_legacy(payload: dict[str, Any], version: str, audit: AuditTracker | None, warnings: WarningTracker | None) -> dict[str, Any]:
    if version == "legacy-v1.2":
        order_id = _require_value(payload.get("order_ref") or payload.get("id"), "order_ref")
        customer = _require_dict(payload.get("customer"), "customer")
        buyer_id = _require_value(customer.get("id"), "customer.id")
        display_name = _require_value(customer.get("name"), "customer.name")
        line_items = _convert_legacy_lines(payload.get("lines"), "lines")
        ship_to = _require_dict(payload.get("shipTo"), "shipTo")
        postal_code = _require_value(ship_to.get("postal_code"), "shipTo.postal_code")
        known_keys = {"order_ref", "id", "customer", "lines", "shipTo", "shipping_method", "shipping", "metadata"}
        method_source = payload.get("shipping_method", payload.get("shipping"))
    else:
        order_id = _require_value(payload.get("id"), "id")
        buyer_id = _require_value(payload.get("customer_id"), "customer_id")
        display_name = _require_value(payload.get("customer_name"), "customer_name")
        line_items = _convert_legacy_lines(payload.get("items"), "items")
        ship_to = _require_dict(payload.get("ship_to"), "ship_to")
        postal_key = "postalCode" if "postalCode" in ship_to else "postal"
        postal_code = _require_value(ship_to.get(postal_key), f"ship_to.{postal_key}")
        known_keys = {"id", "customer_id", "customer_name", "items", "ship_to", "shipping_method", "shipping", "metadata"}
        method_source = payload.get("shipping_method", payload.get("shipping"))

    country = _require_value(ship_to.get("country"), "shipTo.country" if version == "legacy-v1.2" else "ship_to.country")
    unknown_fields = _split_unknown_fields(
        {key: value for key, value in payload.items() if key not in known_keys},
        audit=audit,
        warnings=warnings,
        base_path="metadata.unknownFields",
    )

    metadata: dict[str, Any] = {"source": version}
    if unknown_fields:
        metadata["unknownFields"] = unknown_fields

    return {
        "orderId": order_id,
        "buyer": {"id": buyer_id, "displayName": display_name},
        "lineItems": line_items,
        "shipping": {
            "method": _shipping_method(method_source),
            "address": {"country": country, "postalCode": postal_code},
        },
        "metadata": metadata,
    }


def _convert_v2(payload: dict[str, Any], audit: AuditTracker | None, warnings: WarningTracker | None) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    result["orderId"] = _require_value(result.get("orderId"), "orderId")

    buyer = _require_dict(result.get("buyer"), "buyer")
    buyer["id"] = _require_value(buyer.get("id"), "buyer.id")
    buyer["displayName"] = _require_value(buyer.get("displayName"), "buyer.displayName")

    _require_list(result.get("lineItems"), "lineItems")

    shipping = _require_dict(result.get("shipping"), "shipping")
    shipping["method"] = _shipping_method(shipping.get("method"))
    address = _require_dict(shipping.get("address"), "shipping.address")
    address["country"] = _require_value(address.get("country"), "shipping.address.country")
    address["postalCode"] = _require_value(address.get("postalCode"), "shipping.address.postalCode")

    metadata = result.get("metadata")
    if metadata is None:
        metadata = {"source": "public-v2"}
        result["metadata"] = metadata
    metadata = _require_dict(metadata, "metadata")
    metadata["source"] = _require_value(metadata.get("source") or "public-v2", "metadata.source")

    existing_unknown = metadata.get("unknownFields")
    if existing_unknown is None:
        existing_unknown = {}
    else:
        existing_unknown = _require_dict(existing_unknown, "metadata.unknownFields")

    extra_metadata = {key: value for key, value in metadata.items() if key not in {"source", "unknownFields"}}
    preserved_extra = _split_unknown_fields(
        extra_metadata,
        audit=audit,
        warnings=warnings,
        base_path="metadata.unknownFields",
    )
    merged_unknown = copy.deepcopy(existing_unknown)
    merged_unknown.update(preserved_extra)
    if merged_unknown:
        metadata["unknownFields"] = merged_unknown
    elif "unknownFields" in metadata:
        metadata["unknownFields"] = merged_unknown
    for key in list(metadata.keys()):
        if key not in {"source", "unknownFields"}:
            del metadata[key]

    return result


def _convert_order(payload: Any, audit: AuditTracker | None = None, warnings: WarningTracker | None = None) -> dict[str, Any]:
    payload = _require_mapping(payload)
    version = _payload_version(payload)
    if version == "public-v2":
        return _convert_v2(payload, audit, warnings)
    return _convert_legacy(payload, version, audit, warnings)


def convert_order(payload):
    """Convert a legacy or v2 order payload to the v2 public API shape."""
    return _convert_order(payload)


def summarize_order(v2_payload):
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def _write_audit(converted_count: int, errors: list[dict[str, Any]], warnings: list[dict[str, Any]], audit: AuditTracker) -> None:
    AUDIT_PATH.write_text(
        json.dumps(
            {
                "converted_count": converted_count,
                "error_count": len(errors),
                "warning_count": len(warnings),
                "pii_dropped_count": audit.pii_dropped_count,
                "unknown_fields_count": audit.unknown_fields_count,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def convert_many(payloads: Iterable[Any]):
    converted = []
    errors = []
    warnings = []
    audit = AuditTracker()

    for index, payload in enumerate(payloads):
        warning_tracker = WarningTracker(index)
        try:
            converted.append(_convert_order(payload, audit, warning_tracker))
        except ConversionError as exc:
            errors.append({"index": index, "path": exc.path, "error": exc.error})
        warnings.extend(warning_tracker.warnings)

    _write_audit(len(converted), errors, warnings, audit)
    return converted, errors, warnings


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
                _raise(f"line[{line_number}]", f"invalid JSON: {exc.msg}")
    return payloads


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print("Usage: python -m client input.jsonl output.json", file=sys.stderr)
        return 2

    input_path, output_path = argv
    try:
        payloads = _load_jsonl(input_path)
        converted, errors, warnings = convert_many(payloads)
    except ConversionError as exc:
        print(json.dumps({"path": exc.path, "error": exc.error}), file=sys.stderr)
        return 1

    Path(output_path).write_text(json.dumps(converted, indent=2) + "\n", encoding="utf-8")
    if warnings:
        print(json.dumps({"warnings": warnings}, indent=2), file=sys.stderr)
    if errors:
        print(json.dumps({"errors": errors}, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

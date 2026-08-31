"""Order payload migration helpers and JSON Lines command-line interface."""

from __future__ import annotations

import copy
import json
import sys
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any


PII_KEYS = {
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "phone_number",
    "passport_number",
}

_LEGACY_KEYS = {
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
_AUDIT_PATH = Path(__file__).resolve().with_name("conversion_audit.json")


class ConversionError(ValueError):
    """A conversion failure associated with a useful input path."""

    def __init__(self, path: str, message: str) -> None:
        super().__init__(message)
        self.path = path


class ConversionBatchResult:
    """Backward-compatible two-value result with optional warnings.

    Iteration yields ``converted`` and ``errors`` so existing two-value
    unpacking keeps working. Warnings are available through ``.warnings`` or
    index 2.
    """

    __slots__ = ("converted", "errors", "warnings")

    def __init__(
        self,
        converted: list[dict[str, Any]],
        errors: list[dict[str, Any]],
        warnings: list[dict[str, Any]],
    ) -> None:
        self.converted = converted
        self.errors = errors
        self.warnings = warnings

    def __iter__(self) -> Iterator[list[dict[str, Any]]]:
        yield self.converted
        yield self.errors

    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int | slice) -> Any:
        values = (self.converted, self.errors, self.warnings)
        return values[index]


def _required(mapping: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in mapping:
        raise ConversionError(path, f"missing required field: {path}")
    return mapping[key]


def _as_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConversionError(path, f"expected object at {path}")
    return value


def _as_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConversionError(path, f"expected array at {path}")
    return value


def _as_integer(value: Any, path: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ConversionError(path, f"expected integer at {path}") from exc


def _is_blank_shipping_method(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _legacy_value(
    payload: Mapping[str, Any], first: str, second: str, path: str
) -> Any:
    if first in payload:
        return payload[first]
    if second in payload:
        return payload[second]
    raise ConversionError(path, f"missing required field: {path}")


def _convert_v2(payload: Mapping[str, Any]) -> dict[str, Any]:
    converted = copy.deepcopy(dict(payload))
    shipping = _as_mapping(converted["shipping"], "shipping")
    shipping_copy = dict(shipping)
    if _is_blank_shipping_method(shipping_copy.get("method")):
        shipping_copy["method"] = "standard"
    converted["shipping"] = shipping_copy
    return converted



_DROPPED = object()


def _drop_pii_keys(value: Any) -> tuple[Any, int]:
    """Copy an unknown value while removing sensitive keys at any depth."""
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        dropped = 0
        for key, child in value.items():
            if key in PII_KEYS:
                dropped += 1 + _count_pii_keys(child)
                continue
            cleaned, child_dropped = _drop_pii_keys(child)
            dropped += child_dropped
            if cleaned is not _DROPPED:
                result[key] = cleaned
        return result, dropped
    if isinstance(value, list):
        result_list = []
        dropped = 0
        for child in value:
            cleaned, child_dropped = _drop_pii_keys(child)
            dropped += child_dropped
            if cleaned is not _DROPPED:
                result_list.append(cleaned)
        return result_list, dropped
    return copy.deepcopy(value), 0


def _count_pii_keys(value: Any) -> int:
    if isinstance(value, Mapping):
        return sum((1 + _count_pii_keys(child)) if key in PII_KEYS else _count_pii_keys(child)
                   for key, child in value.items())
    if isinstance(value, list):
        return sum(_count_pii_keys(child) for child in value)
    return 0


def _convert_legacy(payload: Mapping[str, Any]) -> tuple[dict[str, Any], int, int]:
    order_id = _legacy_value(payload, "id", "order_ref", "id")

    if "customer" in payload:
        customer = _as_mapping(payload["customer"], "customer")
        customer_id = _required(customer, "id", "customer.id")
        customer_name = _required(customer, "name", "customer.name")
    else:
        customer_id = _required(payload, "customer_id", "customer_id")
        customer_name = _required(payload, "customer_name", "customer_name")

    item_key = "items" if "items" in payload else "lines"
    raw_items = _as_list(
        _legacy_value(payload, "items", "lines", item_key), item_key
    )
    line_items: list[dict[str, Any]] = []
    for index, raw_item in enumerate(raw_items):
        item_path = f"{item_key}[{index}]"
        item = _as_mapping(raw_item, item_path)
        sku = _required(item, "sku", f"{item_path}.sku")
        quantity = _as_integer(
            _required(item, "qty", f"{item_path}.qty"), f"{item_path}.qty"
        )
        price_key = "price_cents" if "price_cents" in item else "unit_price_cents"
        price = _as_integer(
            _required(item, price_key, f"{item_path}.{price_key}"),
            f"{item_path}.{price_key}",
        )
        line_items.append(
            {"sku": copy.deepcopy(sku), "quantity": quantity, "unitPriceCents": price}
        )

    address_key = "ship_to" if "ship_to" in payload else "shipTo"
    address = _as_mapping(
        _legacy_value(payload, "ship_to", "shipTo", address_key), address_key
    )
    country = _required(address, "country", f"{address_key}.country")
    if "postal" in address:
        postal_code = address["postal"]
    elif "postalCode" in address:
        postal_code = address["postalCode"]
    elif "postal_code" in address:
        postal_code = address["postal_code"]
    else:
        raise ConversionError(
            f"{address_key}.postalCode",
            f"missing required field: {address_key}.postalCode",
        )

    if "shipping_method" in payload:
        shipping_method = payload["shipping_method"]
    else:
        shipping_method = payload.get("shipping")
    if _is_blank_shipping_method(shipping_method):
        shipping_method = "standard"

    unknown_fields: dict[str, Any] = {}
    pii_dropped_count = 0
    for key, value in payload.items():
        if key in PII_KEYS:
            pii_dropped_count += _count_pii_keys(value) + 1
        elif key not in _LEGACY_KEYS:
            cleaned, dropped = _drop_pii_keys(value)
            pii_dropped_count += dropped
            if cleaned is not _DROPPED:
                unknown_fields[key] = cleaned

    metadata: dict[str, Any] = {"source": "legacy-v1"}
    if unknown_fields:
        metadata["unknownFields"] = unknown_fields

    converted = {
        "orderId": copy.deepcopy(order_id),
        "buyer": {
            "id": copy.deepcopy(customer_id),
            "displayName": copy.deepcopy(customer_name),
        },
        "lineItems": line_items,
        "shipping": {
            "method": copy.deepcopy(shipping_method),
            "address": {
                "country": copy.deepcopy(country),
                "postalCode": copy.deepcopy(postal_code),
            },
        },
        "metadata": metadata,
    }
    return converted, pii_dropped_count, len(unknown_fields)


def _convert_order_with_counts(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], int, int]:
    if not isinstance(payload, Mapping):
        raise ConversionError("", "expected order payload object")

    v2_keys = {"orderId", "buyer", "lineItems", "shipping", "metadata"}
    if v2_keys.issubset(payload):
        return _convert_v2(payload), 0, 0
    return _convert_legacy(payload)


def convert_order(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a supported legacy order payload to the public v2 shape."""

    converted, _, _ = _convert_order_with_counts(payload)
    return converted


def _write_audit(audit: Mapping[str, int]) -> None:
    _AUDIT_PATH.write_text(json.dumps(dict(audit), sort_keys=True) + "\n", encoding="utf-8")


def convert_many(payloads: Iterable[Mapping[str, Any]]) -> ConversionBatchResult:
    """Convert orders in sequence, retaining successes after individual errors."""

    converted: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    pii_dropped_count = 0
    unknown_fields_count = 0

    for index, payload in enumerate(payloads):
        try:
            order, pii_count, unknown_count = _convert_order_with_counts(payload)
        except ConversionError as exc:
            errors.append({"index": index, "path": exc.path, "error": str(exc)})
        except Exception as exc:
            errors.append({"index": index, "path": "", "error": str(exc)})
        else:
            converted.append(order)
            pii_dropped_count += pii_count
            unknown_fields_count += unknown_count

    _write_audit(
        {
            "converted_count": len(converted),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "pii_dropped_count": pii_dropped_count,
            "unknown_fields_count": unknown_fields_count,
        }
    )
    return ConversionBatchResult(converted, errors, warnings)


def summarize_order(v2_payload: Mapping[str, Any]) -> str:
    return f"{v2_payload['orderId']}:{len(v2_payload['lineItems'])}"


def _main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} input.jsonl output.json", file=sys.stderr)
        return 2

    input_path = Path(argv[1])
    output_path = Path(argv[2])
    payloads: list[Any] = []
    with input_path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                payloads.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"{input_path}:{line_number}: {exc}", file=sys.stderr)
                return 1

    result = convert_many(payloads)
    with output_path.open("w", encoding="utf-8") as destination:
        json.dump(result.converted, destination, separators=(",", ":"))
        destination.write("\n")

    for error in result.errors:
        print(
            f"record {error['index']} {error['path']}: {error['error']}",
            file=sys.stderr,
        )
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))

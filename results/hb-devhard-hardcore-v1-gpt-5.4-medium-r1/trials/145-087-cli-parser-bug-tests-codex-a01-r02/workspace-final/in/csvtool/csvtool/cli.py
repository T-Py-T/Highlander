from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import build_predicate, parse_where, select_fields


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = list(reader)
    return headers, rows


def parse_select(fields):
    if not fields:
        return None
    return fields.split(",")


def ensure_fields_exist(headers, names, option_name):
    missing = [name for name in names if name not in headers]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"{option_name} references missing field(s): {joined}")


def numeric_sort_key(value):
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        try:
            return (0, float(value))
        except (TypeError, ValueError):
            return (1, value)


def normalize_argv(argv):
    items = list(sys.argv[1:] if argv is None else argv)
    normalized = []
    index = 0
    while index < len(items):
        item = items[index]
        if item == "--sort" and index + 1 < len(items):
            normalized.append(f"--sort={items[index + 1]}")
            index += 2
            continue
        normalized.append(item)
        index += 1
    return normalized


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append", default=[])
    parser.add_argument("--select")
    parser.add_argument("--sort")
    args = parser.parse_args(normalize_argv(argv))

    try:
        headers, rows = read_rows(args.csv_file)

        filters = [parse_where(expr) for expr in args.where]
        ensure_fields_exist(headers, [field for field, _ in filters if field], "--where")

        selected_fields = parse_select(args.select)
        if selected_fields:
            ensure_fields_exist(headers, selected_fields, "--select")

        sort_field = None
        descending = False
        if args.sort:
            descending = args.sort.startswith("-")
            sort_field = args.sort[1:] if descending else args.sort
            if not sort_field:
                raise ValueError("--sort requires a field name")
            ensure_fields_exist(headers, [sort_field], "--sort")

        predicate = build_predicate(filters)
        rows = [row for row in rows if predicate(row)]

        if sort_field:
            rows.sort(key=lambda row: numeric_sort_key(row[sort_field]), reverse=descending)

        output_headers = selected_fields or headers
        rows = select_fields(rows, args.select)

        writer = csv.DictWriter(sys.stdout, fieldnames=output_headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return 0
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

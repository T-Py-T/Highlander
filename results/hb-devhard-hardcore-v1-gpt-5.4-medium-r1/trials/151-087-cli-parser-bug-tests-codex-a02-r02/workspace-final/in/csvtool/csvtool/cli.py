from __future__ import annotations

import argparse
import csv
import sys
from io import StringIO

from csvtool.filtering import parse_where, select_fields


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = list(reader)
    return headers, rows


def parse_sort(sort_expr, headers):
    if not sort_expr:
        return None, False
    descending = sort_expr.startswith("-")
    field = sort_expr[1:] if descending else sort_expr
    if field not in headers:
        raise ValueError(f"Unknown sort field: {field}")
    return field, descending


def numeric_key(value):
    try:
        return 0, float(value)
    except (TypeError, ValueError):
        return 1, value


def write_rows(headers, rows):
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def normalize_argv(argv):
    if argv is None:
        argv = sys.argv[1:]
    normalized = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--sort" and index + 1 < len(argv) and argv[index + 1].startswith("-"):
            normalized.append(f"--sort={argv[index + 1]}")
            index += 2
            continue
        normalized.append(arg)
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
        conditions = [parse_where(expr) for expr in args.where]
        for field, _value in [condition for condition in conditions if condition]:
            if field not in headers:
                raise ValueError(f"Unknown filter field: {field}")
        rows = [
            row
            for row in rows
            if all(condition is None or row[condition[0]] == condition[1] for condition in conditions)
        ]
        sort_field, descending = parse_sort(args.sort, headers)
        if sort_field:
            rows.sort(key=lambda row: numeric_key(row[sort_field]), reverse=descending)
        rows, output_headers = select_fields(rows, args.select, headers)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    sys.stdout.write(write_rows(output_headers, rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

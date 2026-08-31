from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal, InvalidOperation

from csvtool.filtering import parse_where, select_fields


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or has no header")
        headers = list(reader.fieldnames)
        rows = []
        for row in reader:
            if None in row:
                raise ValueError("CSV row has more fields than the header")
            rows.append(dict(row))
    return headers, rows


def _sort_key(value: str):
    try:
        return (0, Decimal(value))
    except (InvalidOperation, ValueError):
        return (1, value)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append", default=[])
    parser.add_argument("--select")
    parser.add_argument("--sort")

    # argparse treats a value beginning with '-' as another option.  Normalize
    # the documented ``--sort -field`` spelling before parsing it.
    arguments = list(sys.argv[1:] if argv is None else argv)
    for index, argument in enumerate(arguments[:-1]):
        if argument == "--sort" and arguments[index + 1].startswith("-"):
            arguments[index:index + 2] = [f"--sort={arguments[index + 1]}"]
            break
    args = parser.parse_args(arguments)

    try:
        headers, rows = read_rows(args.csv_file)
        for expression in args.where:
            predicate = parse_where(expression, headers)
            rows = [row for row in rows if predicate(row)]

        sort_field = None
        descending = False
        if args.sort:
            sort_field = args.sort[1:] if args.sort.startswith("-") else args.sort
            sort_field = sort_field.strip()
            if not sort_field or sort_field not in headers:
                raise ValueError(f"unknown field {sort_field!r} in --sort")
            descending = args.sort.startswith("-")
            rows.sort(key=lambda row: _sort_key(row[sort_field]), reverse=descending)

        selected_headers = headers
        if args.select:
            selected_headers = [name.strip() for name in args.select.split(",")]
            rows = select_fields(rows, args.select, headers)
    except (OSError, csv.Error, ValueError) as exc:
        parser.error(str(exc))

    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(selected_headers)
    writer.writerows([[row[header] for header in selected_headers] for row in rows])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import sys

from csvtool.filtering import parse_where, select_fields


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        return headers, list(reader)


def sort_key(value):
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
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    for index in range(len(argv) - 1):
        if argv[index] == "--sort" and argv[index + 1].startswith("-") and not argv[index + 1].startswith("--"):
            argv[index : index + 2] = [f"--sort={argv[index + 1]}"]
            break
    args = parser.parse_args(argv)

    try:
        headers, rows = read_rows(args.csv_file)
        predicates = [parse_where(expr) for expr in args.where]

        for expr in args.where:
            field = expr.split("=", 1)[0] if "=" in expr else ""
            if field not in headers:
                raise ValueError(f"where field not found: {field or '<empty>'}")

        select_names = args.select.split(",") if args.select else headers
        if any(name not in headers for name in select_names):
            missing = next(name for name in select_names if name not in headers)
            raise ValueError(f"select field not found: {missing}")

        sort_name = args.sort[1:] if args.sort and args.sort.startswith("-") else args.sort
        if sort_name and sort_name not in headers:
            raise ValueError(f"sort field not found: {sort_name}")

        rows = [row for row in rows if all(predicate(row) for predicate in predicates)]
        if sort_name:
            rows.sort(key=lambda row: sort_key(row[sort_name]), reverse=args.sort.startswith("-"))

        rows = select_fields(rows, args.select)
        output_headers = select_names
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(output_headers)
        writer.writerows([[row[header] for header in output_headers] for row in rows])
    except (OSError, ValueError, csv.Error) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

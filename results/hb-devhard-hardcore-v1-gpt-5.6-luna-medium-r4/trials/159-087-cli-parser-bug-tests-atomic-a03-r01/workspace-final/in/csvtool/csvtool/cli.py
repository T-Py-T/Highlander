from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import sys

from csvtool.filtering import parse_where, select_fields


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return reader.fieldnames or [], list(reader)


def sort_key(value):
    try:
        number = Decimal(value)
        if number.is_finite():
            return 0, number
    except InvalidOperation:
        pass
    return 1, value


def parse_args(parser, argv):
    arguments = list(sys.argv[1:] if argv is None else argv)
    for index in range(len(arguments) - 1):
        if arguments[index] == "--sort" and arguments[index + 1].startswith("-") and not arguments[index + 1].startswith("--"):
            arguments[index : index + 2] = [f"--sort={arguments[index + 1]}"]
            break
    return parser.parse_args(arguments)


def require_fields(parser, headers, fields, option):
    for field in fields:
        if field not in headers:
            parser.error(f"missing field for {option}: {field}")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append")
    parser.add_argument("--select")
    parser.add_argument("--sort")
    args = parse_args(parser, argv)

    headers, rows = read_rows(args.csv_file)

    predicates = []
    for expression in args.where or []:
        try:
            predicate = parse_where(expression)
        except ValueError as error:
            parser.error(str(error))
        field = expression.split("=", 1)[0]
        require_fields(parser, headers, [field], "--where")
        predicates.append(predicate)

    selected_headers = args.select.split(",") if args.select else headers
    require_fields(parser, headers, selected_headers, "--select")

    descending = bool(args.sort and args.sort.startswith("-"))
    sort_field = args.sort[1:] if descending else args.sort
    if sort_field is not None:
        require_fields(parser, headers, [sort_field], "--sort")

    rows = [row for row in rows if all(predicate(row) for predicate in predicates)]
    if sort_field is not None:
        rows.sort(key=lambda row: sort_key(row[sort_field]), reverse=descending)
    rows = select_fields(rows, args.select)

    writer = csv.DictWriter(sys.stdout, fieldnames=selected_headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

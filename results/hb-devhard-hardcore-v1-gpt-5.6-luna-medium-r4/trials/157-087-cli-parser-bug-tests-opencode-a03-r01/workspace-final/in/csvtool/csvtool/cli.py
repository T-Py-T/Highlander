from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import sys

from csvtool.filtering import parse_where, select_fields


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        try:
            headers = next(reader)
        except StopIteration:
            raise ValueError("CSV file is empty") from None
        return headers, [dict(zip(headers, values)) for values in reader]


def _numeric_or_text(value):
    try:
        return (0, Decimal(value))
    except InvalidOperation:
        return (1, value)


def _field_error(field, headers):
    if field not in headers:
        raise ValueError(f"missing field: {field}")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append")
    parser.add_argument("--select")
    parser.add_argument("--sort")
    if argv is None:
        argv = sys.argv[1:]
    normalized_argv = []
    index = 0
    while index < len(argv):
        if (
            argv[index] == "--sort"
            and index + 1 < len(argv)
            and not argv[index + 1].startswith("--")
        ):
            normalized_argv.extend(("--sort=" + argv[index + 1],))
            index += 2
        else:
            normalized_argv.append(argv[index])
            index += 1
    args = parser.parse_args(normalized_argv)

    try:
        headers, rows = read_rows(args.csv_file)
        predicates = []
        for expr in args.where or []:
            predicate = parse_where(expr)
            field = expr.split("=", 1)[0].strip()
            _field_error(field, headers)
            predicates.append(predicate)

        selected_headers = headers
        if args.select:
            selected_headers = [name.strip() for name in args.select.split(",")]
            for field in selected_headers:
                _field_error(field, headers)

        if args.sort:
            sort_field = args.sort[1:] if args.sort.startswith("-") else args.sort
            _field_error(sort_field, headers)
        rows = [row for row in rows if all(predicate(row) for predicate in predicates)]
        if args.sort:
            rows.sort(
                key=lambda row: _numeric_or_text(row[sort_field]),
                reverse=args.sort.startswith("-"),
            )
        rows = select_fields(rows, ",".join(selected_headers) if args.select else None)

        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(selected_headers)
        writer.writerows([[row[field] for field in selected_headers] for row in rows])
    except (OSError, ValueError, csv.Error) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

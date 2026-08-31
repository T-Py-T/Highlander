from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import parse_where, select_fields


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        headers = reader.fieldnames or []
        return headers, list(reader)


def _numeric_sort_key(value):
    try:
        return 0, float(value)
    except (TypeError, ValueError):
        return 1, value


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append")
    parser.add_argument("--select")
    parser.add_argument("--sort")
    arguments = list(sys.argv[1:] if argv is None else argv)
    # argparse treats a descending field name as an option, so make it an
    # attached value while retaining the documented `--sort -field` syntax.
    for index, argument in enumerate(arguments[:-1]):
        if argument == "--sort" and arguments[index + 1].startswith("-"):
            arguments[index : index + 2] = [f"--sort={arguments[index + 1]}"]
            break
    args = parser.parse_args(arguments)

    try:
        headers, rows = read_rows(args.csv_file)
        where_fields = []
        predicates = []
        for expression in args.where or []:
            predicate = parse_where(expression)
            where_fields.append(expression.partition("=")[0])
            predicates.append(predicate)

        for field in where_fields:
            if field not in headers:
                raise ValueError(f"missing field: {field}")

        selected_headers = headers
        if args.select:
            selected_headers = args.select.split(",")
            for field in selected_headers:
                if field not in headers:
                    raise ValueError(f"missing field: {field}")

        if args.sort:
            sort_field = args.sort[1:] if args.sort.startswith("-") else args.sort
            if sort_field not in headers:
                raise ValueError(f"missing field: {sort_field}")
            rows.sort(
                key=lambda row: _numeric_sort_key(row[sort_field]),
                reverse=args.sort.startswith("-"),
            )

        rows = [row for row in rows if all(predicate(row) for predicate in predicates)]
        rows = select_fields(rows, args.select)
    except (OSError, ValueError, csv.Error) as error:
        parser.error(str(error))

    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(selected_headers)
    for row in rows:
        writer.writerow([row[header] for header in selected_headers])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

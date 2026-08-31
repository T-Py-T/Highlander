from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal, InvalidOperation

from csvtool.filtering import parse_where, select_fields


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        try:
            headers = next(reader)
        except StopIteration:
            return [], []
        rows = [dict(zip(headers, values)) for values in reader]
    return headers, rows


def _numeric_key(value: str):
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

    # argparse interprets a value beginning with '-' as another option. The
    # documented ``--sort -field`` form needs to be normalized first.
    arguments = list(sys.argv[1:] if argv is None else argv)
    for index in range(len(arguments) - 1):
        if arguments[index] == "--sort" and arguments[index + 1].startswith("-"):
            arguments[index:index + 2] = [f"--sort={arguments[index + 1]}"]
            break
    args = parser.parse_args(arguments)

    try:
        headers, rows = read_rows(args.csv_file)
        header_set = set(headers)
        for expression in args.where:
            # Validate field names before evaluating, including on empty results.
            if expression.split("=", 1)[0].strip() not in header_set:
                raise ValueError(f"missing field in --where: {expression.split('=', 1)[0].strip()!r}")
        predicates = [parse_where(expression) for expression in args.where]
        rows = [row for row in rows if all(predicate(row) for predicate in predicates)]

        if args.sort:
            descending = args.sort.startswith("-")
            sort_field = args.sort[1:] if descending else args.sort
            if not sort_field or sort_field not in header_set:
                raise ValueError(f"missing field in --sort: {sort_field!r}")
            rows.sort(key=lambda row: _numeric_key(row[sort_field]), reverse=descending)

        selected_headers = headers
        if args.select:
            selected_headers = [name.strip() for name in args.select.split(",")]
            missing = [name for name in selected_headers if name not in header_set]
            if missing:
                raise ValueError(f"missing field in --select: {missing[0]!r}")
            rows = select_fields(rows, args.select)

        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(selected_headers)
        for row in rows:
            writer.writerow([row[header] for header in selected_headers])
        return 0
    except (OSError, csv.Error, ValueError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())

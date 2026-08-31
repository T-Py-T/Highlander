from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal, InvalidOperation

from csvtool.filtering import parse_where, select_fields


class CliError(ValueError):
    """An input error that should be reported without a traceback."""


def read_rows(path):
    try:
        with open(path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise CliError(f"CSV file {path!r} has no header")
            headers = list(reader.fieldnames)
            if any(header is None or header == "" for header in headers):
                raise CliError("CSV header contains an empty field name")
            rows = []
            for row in reader:
                if None in row:
                    raise CliError("CSV row has more fields than the header")
                if any(value is None for value in row.values()):
                    raise CliError("CSV row has fewer fields than the header")
                rows.append(dict(row))
            return headers, rows
    except OSError as exc:
        raise CliError(str(exc)) from exc
    except csv.Error as exc:
        raise CliError(f"invalid CSV: {exc}") from exc


def numeric_or_text(value: str):
    try:
        return (0, Decimal(value))
    except InvalidOperation:
        return (1, value)


def _normalize_sort_argument(argv):
    """Allow argparse to consume a sort value beginning with '-'."""
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    normalized = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--sort" and index + 1 < len(argv):
            normalized.append("--sort=" + argv[index + 1])
            index += 2
        else:
            normalized.append(arg)
            index += 1
    return normalized


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append", default=[])
    parser.add_argument("--select")
    parser.add_argument("--sort")
    args = parser.parse_args(_normalize_sort_argument(argv))

    try:
        headers, rows = read_rows(args.csv_file)
        header_set = set(headers)

        predicates = [parse_where(expr) for expr in args.where]
        for expr in args.where:
            field = expr.split("=", 1)[0] if "=" in expr else ""
            if field not in header_set:
                raise CliError(f"--where references missing field {field!r}")
        rows = [row for row in rows if all(predicate(row) for predicate in predicates)]

        sort_field = None
        descending = False
        if args.sort:
            sort_field = args.sort
            if sort_field.startswith("-"):
                descending = True
                sort_field = sort_field[1:]
            if not sort_field or sort_field not in header_set:
                raise CliError(f"--sort references missing field {sort_field!r}")
            rows.sort(key=lambda row: numeric_or_text(row[sort_field]), reverse=descending)

        selected_headers = headers
        if args.select:
            selected_headers = args.select.split(",")
            for field in selected_headers:
                if not field or field not in header_set:
                    raise CliError(f"--select references missing field {field!r}")
            rows = select_fields(rows, args.select)

        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(selected_headers)
        writer.writerows([ [row[field] for field in selected_headers] for row in rows ])
        return 0
    except (CliError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

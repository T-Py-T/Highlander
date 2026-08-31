from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import parse_where, select_fields


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def normalize_argv(argv):
    if argv is None:
        argv = sys.argv[1:]

    normalized = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--sort" and i + 1 < len(argv):
            normalized.append(f"--sort={argv[i + 1]}")
            i += 2
            continue

        normalized.append(arg)
        i += 1

    return normalized


def parse_sort(sort_expr, headers):
    if not sort_expr:
        return None, False

    reverse = sort_expr.startswith("-")
    field = sort_expr[1:] if reverse else sort_expr
    if not field:
        raise ValueError("invalid --sort field")
    if field not in set(headers):
        raise ValueError(f"unknown field in --sort: {field}")
    return field, reverse


def sort_key(value):
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, value)


def write_rows(headers, rows):
    writer = csv.DictWriter(sys.stdout, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)


def main(argv=None):
    argv = normalize_argv(argv)
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append", default=[])
    parser.add_argument("--select")
    parser.add_argument("--sort")
    args = parser.parse_args(argv)

    try:
        headers, rows = read_rows(args.csv_file)
        predicate = parse_where(args.where, headers)
        rows = [row for row in rows if predicate(row)]

        sort_field, reverse = parse_sort(args.sort, headers)
        if sort_field:
            rows.sort(key=lambda row: sort_key(row[sort_field]), reverse=reverse)

        rows, output_headers = select_fields(rows, args.select, headers)
        write_rows(output_headers, rows)
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

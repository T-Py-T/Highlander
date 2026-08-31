from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import parse_where, select_fields


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def numeric_sort_key(value):
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, str(value))


def normalize_argv(argv):
    if argv is None:
        argv = sys.argv[1:]

    normalized = []
    index = 0
    while index < len(argv):
        if argv[index] == "--sort" and index + 1 < len(argv):
            normalized.append(f"--sort={argv[index + 1]}")
            index += 2
            continue
        normalized.append(argv[index])
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
        for field, _ in filters:
            if field not in headers:
                raise ValueError(f"missing field: {field}")
        for field, value in filters:
            rows = [row for row in rows if row[field] == value]

        if args.sort:
            reverse = args.sort.startswith("-")
            sort_field = args.sort[1:] if reverse else args.sort
            if sort_field not in headers:
                raise ValueError(f"missing field: {sort_field}")
            rows.sort(key=lambda row: numeric_sort_key(row[sort_field]), reverse=reverse)

        headers, rows = select_fields(rows, args.select, headers)

        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row[header] for header in headers])
        return 0
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

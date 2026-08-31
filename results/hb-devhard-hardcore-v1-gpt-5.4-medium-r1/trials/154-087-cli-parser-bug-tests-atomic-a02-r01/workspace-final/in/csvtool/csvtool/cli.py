from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import CliUsageError, apply_where, parse_select, parse_where, select_fields


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def sort_key(value):
    try:
        return 0, float(value)
    except (TypeError, ValueError):
        return 1, "" if value is None else str(value)


def write_rows(headers, rows):
    writer = csv.DictWriter(sys.stdout, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({header: row.get(header, "") for header in headers})


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


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append", default=[])
    parser.add_argument("--select")
    parser.add_argument("--sort")
    args = parser.parse_args(normalize_argv(argv))

    try:
        headers, rows = read_rows(args.csv_file)
        predicates = parse_where(args.where, headers)
        rows = apply_where(rows, predicates)

        if args.sort:
            reverse = args.sort.startswith("-")
            sort_field = args.sort[1:] if reverse else args.sort
            if not sort_field:
                raise CliUsageError("sort field not found: ")
            if sort_field not in headers:
                raise CliUsageError(f"sort field not found: {sort_field}")
            rows.sort(key=lambda row: sort_key(row[sort_field]), reverse=reverse)

        selected_headers = parse_select(args.select, headers)
        rows = select_fields(rows, selected_headers)
        write_rows(selected_headers, rows)
        return 0
    except CliUsageError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

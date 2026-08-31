from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import CliUsageError, parse_sort, parse_where, select_fields, sort_value


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def normalize_argv(argv):
    normalized = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--sort" and index + 1 < len(argv):
            normalized.append(f"--sort={argv[index + 1]}")
            index += 2
            continue
        normalized.append(arg)
        index += 1
    return normalized


def main(argv=None):
    argv = normalize_argv(list(sys.argv[1:] if argv is None else argv))
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

        sort_field, descending = parse_sort(args.sort, headers)
        if sort_field:
            rows.sort(key=lambda row: sort_value(row[sort_field]), reverse=descending)

        rows, headers = select_fields(rows, args.select, headers)
    except (OSError, csv.Error, CliUsageError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    writer = csv.DictWriter(sys.stdout, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

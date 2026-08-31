from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import FilterError, apply_predicates, build_predicates, select_fields


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = list(reader)
    return headers, rows


def sort_value(value: str):
    if value is None:
        return (2, "")
    try:
        return (0, int(value))
    except ValueError:
        try:
            return (0, float(value))
        except ValueError:
            return (1, value)


def sort_rows(rows, headers, sort_field):
    if not sort_field:
        return list(rows)
    descending = sort_field.startswith("-")
    field = sort_field[1:] if descending else sort_field
    if field not in headers:
        raise FilterError(f"Unknown field for --sort: {field}")
    return sorted(rows, key=lambda row: sort_value(row[field]), reverse=descending)


def write_rows(headers, rows):
    writer = csv.DictWriter(sys.stdout, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

def normalize_argv(argv):
    if argv is None:
        argv = sys.argv[1:]
    normalized = []
    i = 0
    while i < len(argv):
        current = argv[i]
        if current == "--sort" and i + 1 < len(argv):
            normalized.append(f"--sort={argv[i + 1]}")
            i += 2
            continue
        normalized.append(current)
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
        predicates = build_predicates(args.where, headers)
        rows = apply_predicates(rows, predicates)
        rows = sort_rows(rows, headers, args.sort)
        rows, headers = select_fields(rows, args.select, headers)
        write_rows(headers, rows)
    except (FilterError, FileNotFoundError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

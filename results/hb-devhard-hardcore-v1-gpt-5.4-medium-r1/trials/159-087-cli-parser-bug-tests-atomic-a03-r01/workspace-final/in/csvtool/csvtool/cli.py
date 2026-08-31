from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import compile_predicates, parse_select, row_matches, select_fields


def normalize_argv(argv):
    argv = list(sys.argv[1:] if argv is None else argv)
    normalized = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--sort" and i + 1 < len(argv) and argv[i + 1].startswith("-"):
            normalized.append(f"--sort={argv[i + 1]}")
            i += 2
            continue
        normalized.append(arg)
        i += 1
    return normalized


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def is_number(value):
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    try:
        float(text)
    except ValueError:
        return False
    return True


def sort_key(row, field, numeric):
    value = row[field]
    if numeric:
        return float(value)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append", default=[])
    parser.add_argument("--select")
    parser.add_argument("--sort")

    try:
        args = parser.parse_args(normalize_argv(argv))
        headers, rows = read_rows(args.csv_file)
        predicates = compile_predicates(args.where, headers)
        rows = [row for row in rows if row_matches(row, predicates)]

        if args.sort:
            descending = args.sort.startswith("-")
            sort_field = args.sort[1:] if descending else args.sort
            if sort_field not in headers:
                raise ValueError(f"Unknown field in --sort: {sort_field}")
            numeric = all(is_number(row[sort_field]) for row in rows if row.get(sort_field, "") != "")
            rows.sort(key=lambda row: sort_key(row, sort_field, numeric), reverse=descending)

        selected_headers = parse_select(args.select, headers)
        rows = select_fields(rows, selected_headers)

        writer = csv.DictWriter(sys.stdout, fieldnames=selected_headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return 0
    except ValueError as err:
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

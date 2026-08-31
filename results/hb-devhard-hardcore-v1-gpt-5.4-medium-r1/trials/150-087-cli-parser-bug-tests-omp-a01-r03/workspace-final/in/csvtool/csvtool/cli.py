from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import CsvToolError, parse_select, parse_where, select_fields


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = list(reader)
    if not headers:
        raise CsvToolError("input CSV is missing a header row")
    return headers, rows


def parse_sort(sort_expr: str | None, headers: list[str]):
    if not sort_expr:
        return None, False

    descending = sort_expr.startswith("-")
    field = sort_expr[1:] if descending else sort_expr
    if not field:
        raise CsvToolError("invalid --sort expression '-'")
    if field not in headers:
        raise CsvToolError(f"--sort: unknown field '{field}'")
    return field, descending


def sort_key(value: str):
    try:
        return (0, int(value))
    except ValueError:
        try:
            return (0, float(value))
        except ValueError:
            return (1, value)


def write_rows(headers, rows):
    writer = csv.DictWriter(sys.stdout, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
def normalize_argv(argv):
    if argv is None:
        argv = sys.argv[1:]

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
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append")
    parser.add_argument("--select")
    parser.add_argument("--sort")
    args = parser.parse_args(normalize_argv(argv))

    try:
        headers, rows = read_rows(args.csv_file)
        predicate = parse_where(args.where, headers)
        rows = [row for row in rows if predicate(row)]

        sort_field, descending = parse_sort(args.sort, headers)
        if sort_field:
            rows.sort(key=lambda row: sort_key(row[sort_field]), reverse=descending)

        selected_headers = parse_select(args.select, headers)
        rows = select_fields(rows, selected_headers)
        write_rows(selected_headers, rows)
        return 0
    except CsvToolError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

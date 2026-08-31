from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import parse_where, select_fields


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError("CSV file has no header")
        headers = reader.fieldnames
        rows = list(reader)
    return headers, rows


def _sort_key(value):
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, value)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append", default=[])
    parser.add_argument("--select")
    parser.add_argument("--sort")
    if argv is None:
        argv = sys.argv[1:]
    # argparse treats a descending field (such as -created_at) as an option.
    normalized = []
    index = 0
    while index < len(argv):
        if argv[index] == "--sort" and index + 1 < len(argv) and argv[index + 1].startswith("-"):
            normalized.append("--sort=" + argv[index + 1])
            index += 2
        else:
            normalized.append(argv[index])
            index += 1
    args = parser.parse_args(normalized)

    try:
        headers, rows = read_rows(args.csv_file)
        for expr in args.where:
            predicate = parse_where(expr)
            field = expr.split("=", 1)[0].strip()
            if field not in headers:
                raise ValueError(f"where field not found: {field}")
            rows = [row for row in rows if predicate(row)]

        sort_field = args.sort[1:] if args.sort and args.sort.startswith("-") else args.sort
        if args.sort and not sort_field:
            raise ValueError("sort field not found: (empty)")
        if sort_field:
            if sort_field not in headers:
                raise ValueError(f"sort field not found: {sort_field}")
            rows.sort(key=lambda row: _sort_key(row[sort_field]), reverse=args.sort.startswith("-"))

        rows, selected_headers = select_fields(rows, args.select, headers)
        output = csv.writer(sys.stdout, lineterminator="\n")
        output.writerow(selected_headers)
        output.writerows([[row.get(header, "") for header in selected_headers] for row in rows])
        return 0
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())

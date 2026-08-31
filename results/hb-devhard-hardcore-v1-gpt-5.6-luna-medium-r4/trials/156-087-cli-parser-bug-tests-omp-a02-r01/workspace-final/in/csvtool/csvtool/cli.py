from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import parse_where, select_fields


def read_rows(path):
    try:
        with open(path, newline="", encoding="utf-8") as stream:
            reader = csv.reader(stream)
            headers = next(reader)
            rows = []
            for line_number, values in enumerate(reader, start=2):
                if len(values) != len(headers):
                    raise ValueError(
                        f"row {line_number} has {len(values)} fields; expected {len(headers)}"
                    )
                rows.append(dict(zip(headers, values)))
    except StopIteration:
        raise ValueError("CSV file is empty")
    return headers, rows


def _sort_key(field):
    def key(row):
        value = row[field]
        try:
            return (0, float(value))
        except ValueError:
            return (1, value)

    return key


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append", default=[])
    parser.add_argument("--select")
    parser.add_argument("--sort")
    if argv is None:
        argv = sys.argv[1:]
    # argparse treats a separate "-field" token as another option.
    normalized = []
    index = 0
    while index < len(argv):
        if argv[index] == "--sort" and index + 1 < len(argv):
            normalized.append(f"--sort={argv[index + 1]}")
            index += 2
        else:
            normalized.append(argv[index])
            index += 1
    args = parser.parse_args(normalized)

    try:
        headers, rows = read_rows(args.csv_file)
        predicates = [parse_where(expr, headers) for expr in args.where]
        rows = [row for row in rows if all(predicate(row) for predicate in predicates)]

        if args.sort:
            sort_field = args.sort[1:] if args.sort.startswith("-") else args.sort
            if not sort_field or sort_field not in headers:
                raise ValueError(f"unknown field {sort_field!r} in --sort")
            rows.sort(key=_sort_key(sort_field), reverse=args.sort.startswith("-"))

        selected = select_fields(rows, args.select, headers)
        output_headers = (
            [name.strip() for name in args.select.split(",")]
            if args.select
            else headers
        )
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(output_headers)
        writer.writerows(
            [[row[header] for header in output_headers] for row in selected]
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import parse_where, select_fields


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames
        if not headers:
            raise ValueError("CSV file has no header")
        return headers, list(reader)


def _numeric_or_text(value):
    try:
        return 0, float(value)
    except (TypeError, ValueError):
        return 1, str(value)


def main(argv=None):
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    for index, token in enumerate(raw_argv[:-1]):
        if token == "--sort" and raw_argv[index + 1].startswith("-"):
            raw_argv[index:index + 2] = [f"--sort={raw_argv[index + 1]}"]
            break
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append", default=[])
    parser.add_argument("--select")
    parser.add_argument("--sort")
    args = parser.parse_args(raw_argv)

    try:
        headers, rows = read_rows(args.csv_file)
        predicates = [parse_where(expr) for expr in args.where]
        for predicate in predicates:
            if predicate.field not in headers:
                raise ValueError(f"missing field in --where: {predicate.field}")

        selected = args.select.split(",") if args.select else headers
        missing = [name for name in selected if name not in headers]
        if missing:
            raise ValueError(f"missing field in --select: {missing[0]}")

        sort_field = args.sort
        descending = bool(sort_field and sort_field.startswith("-"))
        if descending:
            sort_field = sort_field[1:]
        if args.sort and sort_field not in headers:
            raise ValueError(f"missing field in --sort: {sort_field}")

        for predicate in predicates:
            rows = [row for row in rows if predicate(row)]
        if sort_field:
            rows.sort(key=lambda row: _numeric_or_text(row[sort_field]), reverse=descending)
        rows = select_fields(rows, args.select)

        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(selected)
        writer.writerows([row[name] for name in selected] for row in rows)
        return 0
    except (OSError, csv.Error, ValueError) as exc:
        parser.error(str(exc))



if __name__ == "__main__":
    raise SystemExit(main())

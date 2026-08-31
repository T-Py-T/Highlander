from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import FieldError, parse_where, select_fields


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        return headers, list(reader)


def _numeric_or_text(value):
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, str(value))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--where", action="append")
    parser.add_argument("--select")
    parser.add_argument("--sort")
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    if "--sort" in argv:
        index = argv.index("--sort")
        if index + 1 < len(argv) and argv[index + 1].startswith("-"):
            argv[index : index + 2] = [f"--sort={argv[index + 1]}"]
    args = parser.parse_args(argv)

    try:
        headers, rows = read_rows(args.csv_file)
        predicates = []
        for expr in args.where or []:
            if expr.count("=") != 1:
                raise ValueError(
                    f"invalid --where expression {expr!r}; expected FIELD=VALUE"
                )
            field = expr.split("=", 1)[0]
            if field not in headers:
                raise FieldError(f"--where field {field!r} not found in CSV")
            predicates.append(parse_where(expr))

        if args.sort:
            sort_field = args.sort[1:] if args.sort.startswith("-") else args.sort
            if not sort_field or sort_field not in headers:
                raise FieldError(f"--sort field {sort_field!r} not found in CSV")
        else:
            sort_field = None

        if args.select:
            selected_headers = args.select.split(",")
            if any(not field for field in selected_headers):
                raise ValueError(
                    "invalid --select value; expected comma-separated field names"
                )
            missing = next((field for field in selected_headers if field not in headers), None)
            if missing is not None:
                raise FieldError(f"--select field {missing!r} not found in CSV")
        else:
            selected_headers = headers

        rows = [row for row in rows if all(predicate(row) for predicate in predicates)]
        if sort_field:
            rows.sort(
                key=lambda row: _numeric_or_text(row[sort_field]),
                reverse=args.sort.startswith("-"),
            )
        rows = select_fields(rows, args.select)
    except (OSError, csv.Error, ValueError) as error:
        print(f"csvtool: {error}", file=sys.stderr)
        return 2

    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(selected_headers)
    writer.writerows([[row[field] for field in selected_headers] for row in rows])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import parse_select, parse_where


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def require_fields(headers, names, option_name):
    missing = [name for name in names if name not in headers]
    if missing:
        quoted = ", ".join(repr(name) for name in missing)
        raise ValueError(f"{option_name} references missing field(s): {quoted}")


def sort_key(value):
    if value is None:
        return (1, "")

    text = str(value)
    try:
        return (0, float(text))
    except ValueError:
        return (1, text)


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

        filters = [parse_where(expr) for expr in args.where]
        require_fields(headers, [field for field, _value in filters], "--where")

        selected_headers = parse_select(args.select) or headers
        require_fields(headers, selected_headers, "--select")

        if args.sort:
            descending = args.sort.startswith("-")
            sort_field = args.sort[1:] if descending else args.sort
            if not sort_field:
                raise ValueError("invalid --sort value: field name is required")
            require_fields(headers, [sort_field], "--sort")
        else:
            descending = False
            sort_field = None

        for field, expected in filters:
            rows = [row for row in rows if row[field] == expected]

        if sort_field:
            rows.sort(key=lambda row: sort_key(row[sort_field]), reverse=descending)

        writer = csv.DictWriter(sys.stdout, fieldnames=selected_headers, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in selected_headers})
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

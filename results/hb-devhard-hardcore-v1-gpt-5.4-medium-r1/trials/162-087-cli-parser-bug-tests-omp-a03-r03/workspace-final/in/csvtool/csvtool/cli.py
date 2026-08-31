from __future__ import annotations

import argparse
import csv
import sys

from csvtool.filtering import compile_predicates, parse_where, select_fields


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def parse_selected_headers(select):
    if not select:
        return None
    return select.split(",")


def require_fields(headers, names, option):
    missing = [name for name in names if name not in headers]
    if missing:
        raise KeyError(f"{option} field not found: {', '.join(missing)}")


def sort_key(value):
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, value)


def write_rows(headers, rows):
    writer = csv.DictWriter(sys.stdout, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)


def normalize_argv(argv):
    tokens = list(sys.argv[1:] if argv is None else argv)
    normalized = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--sort" and index + 1 < len(tokens) and tokens[index + 1].startswith("-"):
            normalized.append(f"--sort={tokens[index + 1]}")
            index += 2
            continue
        normalized.append(token)
        index += 1
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

        if args.where:
            parsed_where = [parse_where(expr) for expr in args.where]
            require_fields(headers, [field for field, _ in parsed_where], "--where")
            predicates = compile_predicates(args.where)
            rows = [row for row in rows if predicates(row)]

        selected_headers = parse_selected_headers(args.select)
        if selected_headers is not None:
            require_fields(headers, selected_headers, "--select")

        if args.sort:
            descending = args.sort.startswith("-")
            field = args.sort[1:] if descending else args.sort
            require_fields(headers, [field], "--sort")
            rows.sort(key=lambda row: sort_key(row[field]), reverse=descending)

        if selected_headers is not None:
            rows = select_fields(rows, args.select)
            headers = selected_headers

        write_rows(headers, rows)
        return 0
    except (KeyError, ValueError) as exc:
        print(exc.args[0] if exc.args else str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

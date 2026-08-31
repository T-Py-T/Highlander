import csv
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "csvtool.cli", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def run_with_csv(fieldnames, rows, *args):
    with tempfile.TemporaryDirectory() as directory:
        csv_path = Path(directory) / "input.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return run_cli(str(csv_path), *args)


def output_rows(proc):
    assert proc.returncode == 0, proc.stderr
    return list(csv.DictReader(proc.stdout.splitlines()))


def test_quoted_comma_round_trips_as_csv():
    proc = run_with_csv(
        ["id", "customer"],
        [{"id": "1", "customer": "Ava, Inc"}],
        "--select",
        "id,customer",
    )

    assert output_rows(proc) == [{"id": "1", "customer": "Ava, Inc"}]
    assert '"Ava, Inc"' in proc.stdout


def test_repeated_where_predicates_use_and():
    proc = run_with_csv(
        ["id", "status", "region"],
        [
            {"id": "1", "status": "paid", "region": "west"},
            {"id": "2", "status": "paid", "region": "east"},
            {"id": "3", "status": "pending", "region": "west"},
        ],
        "--where",
        "status=paid",
        "--where",
        "region=west",
        "--select",
        "id",
    )

    assert output_rows(proc) == [{"id": "1"}]


def test_empty_selected_result_prints_selected_header():
    proc = run_with_csv(
        ["id", "status", "total"],
        [{"id": "1", "status": "paid", "total": "10"}],
        "--where",
        "status=refunded",
        "--select",
        "id,total",
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "id,total\n"


def test_numeric_sort_ascending_and_descending():
    fields = ["id", "amount"]
    rows = [
        {"id": "a", "amount": "10"},
        {"id": "b", "amount": "2"},
        {"id": "c", "amount": "1"},
    ]

    ascending = run_with_csv(fields, rows, "--sort", "amount", "--select", "id,amount")
    descending = run_with_csv(fields, rows, "--sort", "-amount", "--select", "id,amount")

    assert [row["id"] for row in output_rows(ascending)] == ["c", "b", "a"]
    assert [row["id"] for row in output_rows(descending)] == ["a", "b", "c"]


def test_malformed_where_is_a_clear_error():
    proc = run_with_csv(["id"], [{"id": "1"}], "--where", "id")

    assert proc.returncode != 0
    assert "malformed --where" in proc.stderr
    assert proc.stdout == ""


def test_missing_where_field_is_a_clear_error():
    proc = run_with_csv(["id"], [{"id": "1"}], "--where", "missing=value")

    assert proc.returncode != 0
    assert "missing field for --where: missing" in proc.stderr
    assert proc.stdout == ""


def test_missing_select_field_is_a_clear_error():
    proc = run_with_csv(["id"], [{"id": "1"}], "--select", "id,missing")

    assert proc.returncode != 0
    assert "missing field for --select: missing" in proc.stderr
    assert proc.stdout == ""


def test_missing_sort_field_is_a_clear_error():
    proc = run_with_csv(["id"], [{"id": "1"}], "--sort", "missing")

    assert proc.returncode != 0
    assert "missing field for --sort: missing" in proc.stderr
    assert proc.stdout == ""


def test_missing_fields_are_validated_when_results_are_empty():
    proc = run_with_csv(
        ["id", "status"],
        [{"id": "1", "status": "paid"}],
        "--where",
        "status=refunded",
        "--select",
        "missing",
    )

    assert proc.returncode != 0
    assert "missing field for --select: missing" in proc.stderr
    assert proc.stdout == ""

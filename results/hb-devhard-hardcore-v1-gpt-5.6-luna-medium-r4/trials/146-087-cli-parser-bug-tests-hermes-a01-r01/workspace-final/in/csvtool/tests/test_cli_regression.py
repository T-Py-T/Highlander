import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "csvtool.cli", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_repeated_where_uses_and_semantics():
    proc = run_cli(
        "samples/orders.csv",
        "--where", "status=paid",
        "--where", "total=750",
        "--select", "id,total",
    )
    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [{"id": "o3", "total": "750"}]


def test_empty_result_is_a_valid_csv_with_selected_header():
    proc = run_cli("samples/orders.csv", "--where", "status=refunded", "--select", "id,customer")
    assert proc.returncode == 0, proc.stderr
    assert list(csv.reader(proc.stdout.splitlines())) == [["id", "customer"]]


def test_quoted_commas_are_written_quoted():
    proc = run_cli("samples/orders.csv", "--where", "id=o1", "--select", "id,customer")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == ["id,customer", 'o1,"Ava, Inc"']


def test_numeric_descending_sort():
    proc = run_cli("samples/orders.csv", "--select", "id,total", "--sort", "-total")
    assert proc.returncode == 0, proc.stderr
    assert [row["id"] for row in csv.DictReader(proc.stdout.splitlines())] == ["o1", "o3", "o2"]


def test_bad_where_and_missing_fields_fail_clearly():
    bad_where = run_cli("samples/orders.csv", "--where", "status")
    missing = run_cli("samples/orders.csv", "--select", "nope")
    assert bad_where.returncode != 0
    assert "bad --where" in bad_where.stderr
    assert missing.returncode != 0
    assert "missing field" in missing.stderr

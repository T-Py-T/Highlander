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
        "--where",
        "status=paid",
        "--where",
        "total=750",
        "--select",
        "id,customer",
    )

    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [
        {"id": "o3", "customer": "Core, Labs"}
    ]


def test_sort_numeric_values_in_both_directions():
    ascending = run_cli("samples/orders.csv", "--select", "id,total", "--sort", "total")
    descending = run_cli("samples/orders.csv", "--select", "id,total", "--sort", "-total")

    assert ascending.returncode == 0
    assert [row["total"] for row in csv.DictReader(ascending.stdout.splitlines())] == [
        "500",
        "750",
        "1200",
    ]
    assert descending.returncode == 0
    assert [row["total"] for row in csv.DictReader(descending.stdout.splitlines())] == [
        "1200",
        "750",
        "500",
    ]


def test_invalid_where_and_missing_fields_are_reported():
    bad_where = run_cli("samples/orders.csv", "--where", "status")
    missing = run_cli("samples/orders.csv", "--select", "id,missing")

    assert bad_where.returncode != 0
    assert "where expression" in bad_where.stderr
    assert missing.returncode != 0
    assert "select field not found" in missing.stderr


def test_missing_filter_and_sort_fields_are_reported():
    missing_filter = run_cli("samples/orders.csv", "--where", "missing=value")
    missing_sort = run_cli("samples/orders.csv", "--sort", "-missing")

    assert missing_filter.returncode != 0
    assert "where field not found" in missing_filter.stderr
    assert missing_sort.returncode != 0
    assert "sort field not found" in missing_sort.stderr

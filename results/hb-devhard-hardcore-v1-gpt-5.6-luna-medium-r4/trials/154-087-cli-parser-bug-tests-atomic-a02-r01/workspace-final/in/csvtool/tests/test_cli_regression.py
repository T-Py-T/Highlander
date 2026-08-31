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


def test_numeric_ascending_sort_is_numeric():
    proc = run_cli("samples/orders.csv", "--select", "id,total", "--sort", "total")
    assert proc.returncode == 0, proc.stderr
    assert [row["id"] for row in csv.DictReader(proc.stdout.splitlines())] == ["o2", "o3", "o1"]


def test_invalid_where_and_missing_fields_fail_clearly():
    bad_where = run_cli("samples/orders.csv", "--where", "status")
    assert bad_where.returncode != 0
    assert "invalid --where expression" in bad_where.stderr

    missing = run_cli("samples/orders.csv", "--select", "unknown")
    assert missing.returncode != 0

    missing_where = run_cli("samples/orders.csv", "--where", "unknown=value")
    assert missing_where.returncode != 0
    assert "where field not found" in missing_where.stderr
    assert "select field not found" in missing.stderr

    missing_sort = run_cli("samples/orders.csv", "--sort", "unknown")
    assert missing_sort.returncode != 0
    assert "sort field not found" in missing_sort.stderr


def test_quoted_comma_is_quoted_in_output():
    proc = run_cli("samples/orders.csv", "--where", "id=o1", "--select", "customer")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == ["customer", '"Ava, Inc"']

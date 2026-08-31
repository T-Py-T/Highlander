import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "csvtool.cli", *args], cwd=ROOT, capture_output=True, text=True)


def test_repeated_where_uses_and_semantics():
    proc = run_cli(
        "samples/orders.csv",
        "--where",
        "status=paid",
        "--where",
        "total=750",
        "--select",
        "id,total",
    )
    assert proc.returncode == 0, proc.stderr
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    assert rows == [{"id": "o3", "total": "750"}]


def test_descending_sort_uses_field_name_without_dash_and_numeric_order():
    proc = run_cli("samples/orders.csv", "--select", "id,total", "--sort", "-total")
    assert proc.returncode == 0, proc.stderr
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    assert rows == [
        {"id": "o1", "total": "1200"},
        {"id": "o3", "total": "750"},
        {"id": "o2", "total": "500"},
    ]


def test_bad_where_expression_exits_non_zero_with_message():
    proc = run_cli("samples/orders.csv", "--where", "status")
    assert proc.returncode != 0
    assert "invalid --where expression" in proc.stderr


def test_missing_where_field_exits_non_zero_with_message():
    proc = run_cli("samples/orders.csv", "--where", "missing=paid")
    assert proc.returncode != 0
    assert "--where references missing field(s): missing" in proc.stderr


def test_missing_select_field_exits_non_zero_with_message():
    proc = run_cli("samples/orders.csv", "--select", "id,missing")
    assert proc.returncode != 0
    assert "--select references missing field(s): missing" in proc.stderr


def test_missing_sort_field_exits_non_zero_with_message():
    proc = run_cli("samples/orders.csv", "--sort", "-missing")
    assert proc.returncode != 0
    assert "--sort references missing field(s): missing" in proc.stderr

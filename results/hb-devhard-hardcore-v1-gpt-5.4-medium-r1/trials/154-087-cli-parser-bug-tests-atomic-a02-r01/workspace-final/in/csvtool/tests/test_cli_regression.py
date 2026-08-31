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


def test_descending_sort_uses_numeric_order():
    proc = run_cli("samples/orders.csv", "--select", "id,total", "--sort", "-total")
    assert proc.returncode == 0, proc.stderr
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    assert rows == [
        {"id": "o1", "total": "1200"},
        {"id": "o3", "total": "750"},
        {"id": "o2", "total": "500"},
    ]


def test_output_preserves_quoted_commas():
    proc = run_cli("samples/orders.csv", "--where", "id=o1", "--select", "id,customer")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == 'id,customer\no1,"Ava, Inc"\n'


def test_bad_where_expression_exits_non_zero_with_clear_message():
    proc = run_cli("samples/orders.csv", "--where", "status")
    assert proc.returncode != 0
    assert "bad --where expression" in proc.stderr


def test_missing_fields_exit_non_zero_with_clear_message():
    cases = [
        (("samples/orders.csv", "--where", "missing=value"), "filter field not found: missing"),
        (("samples/orders.csv", "--select", "missing"), "select field not found: missing"),
        (("samples/orders.csv", "--sort", "missing"), "sort field not found: missing"),
    ]

    for args, message in cases:
        proc = run_cli(*args)
        assert proc.returncode != 0
        assert message in proc.stderr

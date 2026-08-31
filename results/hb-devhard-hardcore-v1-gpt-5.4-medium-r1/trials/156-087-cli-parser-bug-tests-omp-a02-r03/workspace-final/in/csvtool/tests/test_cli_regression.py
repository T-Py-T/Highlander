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


def test_descending_numeric_sort_orders_largest_first(tmp_path):
    csv_file = tmp_path / "scores.csv"
    csv_file.write_text(
        "id,total\nsmall,2\nlarge,10\nmedium,3\n",
        encoding="utf-8",
    )

    proc = run_cli(str(csv_file), "--select", "id,total", "--sort", "-total")
    assert proc.returncode == 0, proc.stderr
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    assert rows == [
        {"id": "large", "total": "10"},
        {"id": "medium", "total": "3"},
        {"id": "small", "total": "2"},
    ]


def test_invalid_where_expression_exits_nonzero():
    proc = run_cli("samples/orders.csv", "--where", "status")
    assert proc.returncode != 0
    assert "Invalid --where expression" in proc.stderr


def test_missing_fields_exit_nonzero_with_clear_message():
    select_proc = run_cli("samples/orders.csv", "--select", "missing")
    assert select_proc.returncode != 0
    assert "Unknown field for --select: missing" in select_proc.stderr

    sort_proc = run_cli("samples/orders.csv", "--sort", "-missing")
    assert sort_proc.returncode != 0
    assert "Unknown field for --sort: missing" in sort_proc.stderr

    where_proc = run_cli("samples/orders.csv", "--where", "missing=value")
    assert where_proc.returncode != 0
    assert "Unknown field for --where: missing" in where_proc.stderr

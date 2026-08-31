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


def test_bad_where_expression_exits_non_zero_with_clear_message():
    proc = run_cli("samples/orders.csv", "--where", "status")

    assert proc.returncode != 0
    assert "invalid --where expression" in proc.stderr


def test_missing_field_errors_are_reported_clearly():
    proc = run_cli("samples/orders.csv", "--sort", "missing_field")

    assert proc.returncode != 0
    assert "unknown field in --sort: missing_field" in proc.stderr

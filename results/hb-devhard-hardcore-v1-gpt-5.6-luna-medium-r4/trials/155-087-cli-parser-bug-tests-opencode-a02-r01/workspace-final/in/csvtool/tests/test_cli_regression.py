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


def test_repeated_where_expressions_use_and_semantics():
    proc = run_cli(
        "samples/orders.csv",
        "--where",
        "status=paid",
        "--where",
        "total=750",
    )

    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [
        {"id": "o3", "status": "paid", "total": "750", "created_at": "2024-01-02", "customer": "Core, Labs"}
    ]


def test_invalid_where_and_missing_fields_are_reported():
    invalid_where = run_cli("samples/orders.csv", "--where", "status")
    missing_select = run_cli("samples/orders.csv", "--select", "unknown")
    missing_sort = run_cli("samples/orders.csv", "--sort", "unknown")
    missing_filter = run_cli("samples/orders.csv", "--where", "unknown=value")

    assert invalid_where.returncode != 0
    assert "FIELD=VALUE" in invalid_where.stderr
    for proc in (missing_select, missing_sort, missing_filter):
        assert proc.returncode != 0
        assert "missing field: unknown" in proc.stderr

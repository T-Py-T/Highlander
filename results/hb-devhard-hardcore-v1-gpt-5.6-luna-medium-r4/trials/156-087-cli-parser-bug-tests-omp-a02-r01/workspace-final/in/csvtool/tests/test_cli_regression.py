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


def test_numeric_ascending_sort_is_numeric():
    proc = run_cli("samples/orders.csv", "--sort", "total", "--select", "id,total")
    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [
        {"id": "o2", "total": "500"},
        {"id": "o3", "total": "750"},
        {"id": "o1", "total": "1200"},
    ]


def test_invalid_where_and_missing_fields_are_reported():
    for args, message in [
        (("--where", "status"), "expected FIELD=VALUE"),
        (("--where", "missing=x"), "unknown field"),
        (("--select", "missing"), "unknown field"),
        (("--sort", "missing"), "unknown field"),
    ]:
        proc = run_cli("samples/orders.csv", *args)
        assert proc.returncode != 0
        assert message in proc.stderr

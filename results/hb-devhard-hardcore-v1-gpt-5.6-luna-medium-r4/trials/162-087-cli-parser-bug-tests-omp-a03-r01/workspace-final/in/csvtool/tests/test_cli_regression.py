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
        "id,total",
    )
    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [{"id": "o3", "total": "750"}]


def test_numeric_sort_is_ascending_by_default():
    proc = run_cli("samples/orders.csv", "--select", "id,total", "--sort", "total")
    assert proc.returncode == 0, proc.stderr
    assert [row["id"] for row in csv.DictReader(proc.stdout.splitlines())] == ["o2", "o3", "o1"]


def test_invalid_where_and_missing_fields_are_errors():
    for args, message in [
        (("--where", "status"), "expected FIELD=VALUE"),
        (("--where", "unknown=x"), "--where field 'unknown' not found"),
        (("--select", "unknown"), "--select field 'unknown' not found"),
        (("--sort", "unknown"), "--sort field 'unknown' not found"),
    ]:
        proc = run_cli("samples/orders.csv", *args)
        assert proc.returncode != 0
        assert message in proc.stderr


def test_quoted_values_are_written_as_valid_csv():
    proc = run_cli("samples/orders.csv", "--where", "id=o1", "--select", "id,customer")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines()[1] == 'o1,"Ava, Inc"'

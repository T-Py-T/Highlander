import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "csvtool.cli", *args], cwd=ROOT, capture_output=True, text=True)


def write_csv(tmp_path, name, rows):
    path = tmp_path / name
    path.write_text(rows, encoding="utf-8")
    return path


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


def test_descending_sort_uses_numeric_order(tmp_path):
    csv_file = write_csv(
        tmp_path,
        "numbers.csv",
        "id,total\na,2\nb,10\nc,1\n",
    )
    proc = run_cli(str(csv_file), "--select", "id,total", "--sort", "-total")
    assert proc.returncode == 0, proc.stderr
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    assert rows == [
        {"id": "b", "total": "10"},
        {"id": "a", "total": "2"},
        {"id": "c", "total": "1"},
    ]


def test_quoted_commas_round_trip_in_output(tmp_path):
    csv_file = write_csv(
        tmp_path,
        "quoted.csv",
        'id,customer,total\n1,"North, West",10\n',
    )
    proc = run_cli(str(csv_file), "--select", "id,customer")
    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [{"id": "1", "customer": "North, West"}]


def test_invalid_where_exits_non_zero_with_clear_message():
    proc = run_cli("samples/orders.csv", "--where", "status")
    assert proc.returncode != 0
    assert "Invalid --where expression" in proc.stderr


def test_missing_field_errors_are_clear():
    for args, expected in [
        (("samples/orders.csv", "--where", "missing=x"), "Unknown field in --where: missing"),
        (("samples/orders.csv", "--select", "id,missing"), "Unknown field in --select: missing"),
        (("samples/orders.csv", "--sort", "missing"), "Unknown field in --sort: missing"),
    ]:
        proc = run_cli(*args)
        assert proc.returncode != 0
        assert expected in proc.stderr

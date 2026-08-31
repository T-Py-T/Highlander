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


def test_repeated_where_clauses_use_and_semantics():
    proc = run_cli("samples/orders.csv", "--where", "status=paid", "--where", "total=750")
    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [
        {"id": "o3", "status": "paid", "total": "750", "created_at": "2024-01-02", "customer": "Core, Labs"}
    ]


def test_sort_numeric_values_descending(tmp_path):
    source = tmp_path / "values.csv"
    source.write_text("id,total\na,9\nb,120\nc,75\n", encoding="utf-8")
    proc = run_cli(str(source), "--select", "id,total", "--sort", "-total")
    assert proc.returncode == 0, proc.stderr
    assert [row["id"] for row in csv.DictReader(proc.stdout.splitlines())] == ["b", "c", "a"]


def test_invalid_where_and_missing_fields_are_reported():
    invalid_where = run_cli("samples/orders.csv", "--where", "status")
    missing_field = run_cli("samples/orders.csv", "--select", "missing")
    assert invalid_where.returncode != 0
    assert "invalid --where expression" in invalid_where.stderr
    assert missing_field.returncode != 0
    assert "missing field: missing" in missing_field.stderr

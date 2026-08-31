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


def write_csv(path, headers, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


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


def test_descending_numeric_sort_uses_numeric_values(tmp_path):
    csv_file = tmp_path / "scores.csv"
    write_csv(
        csv_file,
        ["id", "score"],
        [
            {"id": "a", "score": "2"},
            {"id": "b", "score": "10"},
            {"id": "c", "score": "1"},
        ],
    )

    proc = run_cli(str(csv_file), "--select", "id,score", "--sort", "-score")
    assert proc.returncode == 0, proc.stderr
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    assert rows == [
        {"id": "b", "score": "10"},
        {"id": "a", "score": "2"},
        {"id": "c", "score": "1"},
    ]


def test_empty_result_without_select_keeps_source_header():
    proc = run_cli("samples/orders.csv", "--where", "status=refunded")
    assert proc.returncode == 0, proc.stderr
    rows = proc.stdout.splitlines()
    assert rows == ["id,status,total,created_at,customer"]


def test_bad_where_expression_exits_non_zero():
    proc = run_cli("samples/orders.csv", "--where", "status")
    assert proc.returncode != 0
    assert "Invalid --where expression" in proc.stderr


def test_missing_select_field_exits_non_zero():
    proc = run_cli("samples/orders.csv", "--select", "id,missing")
    assert proc.returncode != 0
    assert "Unknown field" in proc.stderr


def test_missing_sort_field_exits_non_zero():
    proc = run_cli("samples/orders.csv", "--sort", "missing")
    assert proc.returncode != 0
    assert "Unknown sort field" in proc.stderr


def test_missing_filter_field_exits_non_zero():
    proc = run_cli("samples/orders.csv", "--where", "missing=value")
    assert proc.returncode != 0
    assert "Unknown filter field" in proc.stderr

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


def test_empty_result_still_writes_selected_header_with_newline():
    proc = run_cli("samples/orders.csv", "--where", "status=refunded", "--select", "id,total")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "id,total\n"


def test_descending_sort_uses_numeric_values(tmp_path):
    csv_path = tmp_path / "scores.csv"
    csv_path.write_text("id,score\na,2\nb,10\nc,1\n", encoding="utf-8")

    proc = run_cli(str(csv_path), "--select", "id,score", "--sort", "-score")
    assert proc.returncode == 0, proc.stderr
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    assert rows == [
        {"id": "b", "score": "10"},
        {"id": "a", "score": "2"},
        {"id": "c", "score": "1"},
    ]


def test_invalid_where_expression_exits_nonzero_with_clear_message():
    proc = run_cli("samples/orders.csv", "--where", "status")
    assert proc.returncode != 0
    assert "invalid --where expression 'status'; expected field=value" in proc.stderr


def test_missing_field_errors_are_clear():
    proc = run_cli("samples/orders.csv", "--where", "missing=value")
    assert proc.returncode != 0
    assert "--where: unknown field 'missing'" in proc.stderr

    proc = run_cli("samples/orders.csv", "--select", "id,missing")
    assert proc.returncode != 0
    assert "--select: unknown field 'missing'" in proc.stderr

    proc = run_cli("samples/orders.csv", "--sort", "missing")
    assert proc.returncode != 0
    assert "--sort: unknown field 'missing'" in proc.stderr


def test_output_requotes_fields_with_commas():
    proc = run_cli("samples/orders.csv", "--where", "id=o1", "--select", "id,customer")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == 'id,customer\no1,"Ava, Inc"\n'

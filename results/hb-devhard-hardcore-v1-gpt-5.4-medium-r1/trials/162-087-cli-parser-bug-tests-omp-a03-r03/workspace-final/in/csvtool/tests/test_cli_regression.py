import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "csvtool.cli", *args], cwd=ROOT, capture_output=True, text=True)


def write_csv(path, headers, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_repeated_where_uses_and_semantics(tmp_path):
    csv_path = tmp_path / "orders.csv"
    write_csv(
        csv_path,
        ["id", "status", "total"],
        [
            {"id": "o1", "status": "paid", "total": "750"},
            {"id": "o2", "status": "paid", "total": "500"},
            {"id": "o3", "status": "pending", "total": "750"},
        ],
    )

    proc = run_cli(str(csv_path), "--where", "status=paid", "--where", "total=750", "--select", "id,total")

    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [{"id": "o1", "total": "750"}]


def test_selected_output_preserves_quoted_commas(tmp_path):
    csv_path = tmp_path / "customers.csv"
    write_csv(
        csv_path,
        ["id", "customer", "status"],
        [{"id": "o1", "customer": "Ava, Inc", "status": "paid"}],
    )

    proc = run_cli(str(csv_path), "--where", "status=paid", "--select", "id,customer")

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == 'id,customer\no1,"Ava, Inc"\n'


def test_sort_descending_uses_numeric_order(tmp_path):
    csv_path = tmp_path / "orders.csv"
    write_csv(
        csv_path,
        ["id", "total"],
        [
            {"id": "o1", "total": "9"},
            {"id": "o2", "total": "100"},
            {"id": "o3", "total": "20"},
        ],
    )

    proc = run_cli(str(csv_path), "--select", "id,total", "--sort", "-total")

    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [
        {"id": "o2", "total": "100"},
        {"id": "o3", "total": "20"},
        {"id": "o1", "total": "9"},
    ]


def test_invalid_where_expression_exits_non_zero(tmp_path):
    csv_path = tmp_path / "orders.csv"
    write_csv(csv_path, ["id", "status"], [{"id": "o1", "status": "paid"}])

    proc = run_cli(str(csv_path), "--where", "status")

    assert proc.returncode != 0
    assert "Invalid --where expression" in proc.stderr


def test_missing_fields_fail_with_clear_messages(tmp_path):
    csv_path = tmp_path / "orders.csv"
    write_csv(csv_path, ["id", "status"], [{"id": "o1", "status": "paid"}])

    where_proc = run_cli(str(csv_path), "--where", "total=750")
    select_proc = run_cli(str(csv_path), "--select", "id,total")
    sort_proc = run_cli(str(csv_path), "--sort", "total")

    assert where_proc.returncode != 0
    assert where_proc.stderr.strip() == "--where field not found: total"
    assert select_proc.returncode != 0
    assert select_proc.stderr.strip() == "--select field not found: total"
    assert sort_proc.returncode != 0
    assert sort_proc.stderr.strip() == "--sort field not found: total"

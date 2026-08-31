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


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_repeated_where_uses_and_semantics(tmp_path):
    path = tmp_path / "orders.csv"
    write_csv(path, [{"id": "1", "status": "paid", "total": "750"}, {"id": "2", "status": "paid", "total": "1200"}])

    proc = run_cli(str(path), "--where", "status=paid", "--where", "total=750", "--select", "id")

    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [{"id": "1"}]


def test_numeric_sort_is_numeric(tmp_path):
    path = tmp_path / "values.csv"
    write_csv(path, [{"id": "one", "amount": "2"}, {"id": "two", "amount": "10"}, {"id": "three", "amount": "1"}])

    proc = run_cli(str(path), "--sort", "amount", "--select", "id,amount")

    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [
        {"id": "three", "amount": "1"},
        {"id": "one", "amount": "2"},
        {"id": "two", "amount": "10"},
    ]


def test_quoted_comma_is_quoted_in_output(tmp_path):
    path = tmp_path / "customers.csv"
    write_csv(path, [{"id": "1", "customer": "Ava, Inc"}])

    proc = run_cli(str(path), "--select", "id,customer")

    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [{"id": "1", "customer": "Ava, Inc"}]
    assert '"Ava, Inc"' in proc.stdout


def test_invalid_and_missing_fields_are_reported(tmp_path):
    path = tmp_path / "rows.csv"
    write_csv(path, [{"id": "1", "status": "paid"}])

    for option, value in [("--where", "broken"), ("--where", "missing=x"), ("--select", "missing"), ("--sort", "missing")]:
        proc = run_cli(str(path), option, value)
        assert proc.returncode != 0
        assert "error:" in proc.stderr

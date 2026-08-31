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


def test_repeated_where_uses_and_semantics(tmp_path):
    source = tmp_path / "rows.csv"
    source.write_text("id,status,total\na,paid,750\nb,paid,500\nc,pending,750\n")

    proc = run_cli(str(source), "--where", "status=paid", "--where", "total=750")

    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [
        {"id": "a", "status": "paid", "total": "750"}
    ]


def test_quoted_values_round_trip_and_empty_header(tmp_path):
    source = tmp_path / "rows.csv"
    source.write_text('id,customer\na,"Ava, Inc"\n')
    selected = run_cli(str(source), "--where", "id=a", "--select", "id,customer")
    assert selected.returncode == 0, selected.stderr
    assert list(csv.DictReader(selected.stdout.splitlines())) == [{"id": "a", "customer": "Ava, Inc"}]

    empty = run_cli(str(source), "--where", "id=missing", "--select", "id,customer")
    assert empty.returncode == 0
    assert empty.stdout == "id,customer\n"


def test_descending_sort_is_numeric(tmp_path):
    source = tmp_path / "rows.csv"
    source.write_text("id,total\na,2\nb,10\nc,750\n")

    proc = run_cli(str(source), "--sort", "-total", "--select", "id,total")

    assert proc.returncode == 0, proc.stderr
    assert [row["id"] for row in csv.DictReader(proc.stdout.splitlines())] == ["c", "b", "a"]


def test_invalid_where_and_missing_fields_are_errors(tmp_path):
    source = tmp_path / "rows.csv"
    source.write_text("id,status\na,paid\n")

    for args, expected in [
        (("--where", "status"), "invalid --where expression"),
        (("--where", "missing=x"), "missing field in --where"),
        (("--select", "missing"), "missing field in --select"),
        (("--sort", "missing"), "missing field in --sort"),
    ]:
        proc = run_cli(str(source), *args)
        assert proc.returncode != 0
        assert expected in proc.stderr

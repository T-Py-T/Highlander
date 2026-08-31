import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(root, *args):
    return subprocess.run(
        [sys.executable, "-m", "csvtool.cli", *args],
        cwd=root,
        capture_output=True,
        text=True,
    )


def test_repeated_where_uses_and_semantics(tmp_path):
    csv_file = tmp_path / "rows.csv"
    csv_file.write_text("id,status,total\na,paid,750\nb,paid,1200\nc,pending,750\n")
    root = ROOT
    proc = run_cli(root, str(csv_file), "--where", "status=paid", "--where", "total=750")
    assert proc.returncode == 0, proc.stderr
    assert list(csv.DictReader(proc.stdout.splitlines())) == [
        {"id": "a", "status": "paid", "total": "750"}
    ]


def test_numeric_sort_ascending_and_descending(tmp_path):
    csv_file = tmp_path / "rows.csv"
    csv_file.write_text("id,total\na,2\nb,10\nc,1\n")
    root = ROOT
    for sort, expected in [("total", ["c", "a", "b"]), ("-total", ["b", "a", "c"])]:
        proc = run_cli(root, str(csv_file), "--sort", sort, "--select", "id,total")
        assert proc.returncode == 0, proc.stderr
        assert [row["id"] for row in csv.DictReader(proc.stdout.splitlines())] == expected


def test_bad_where_and_missing_fields_fail_clearly():
    root = ROOT
    for args, phrase in [
        (("--where", "status"), "expected FIELD=VALUE"),
        (("--where", "unknown=x"), "missing field"),
        (("--select", "unknown"), "missing field"),
        (("--sort", "unknown"), "missing field"),
    ]:
        proc = run_cli(root, "samples/orders.csv", *args)
        assert proc.returncode != 0
        assert phrase in proc.stderr

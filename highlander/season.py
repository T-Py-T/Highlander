"""Deterministic aggregation for a frozen Highlander benchmark season."""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


class SeasonError(RuntimeError):
    """The season manifest or result ledger is unsafe or inconsistent."""


def load_manifest(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    try:
        manifest = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SeasonError(f"could not load season manifest {source}: {exc}") from exc
    _validate_manifest(manifest)
    return manifest


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path).expanduser().resolve()
    rows: list[dict[str, Any]] = []
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SeasonError(f"could not load result ledger {source}: {exc}") from exc
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SeasonError(f"invalid JSON on result line {number}: {exc}") from exc
        if not isinstance(row, dict):
            raise SeasonError(f"result line {number} must be a JSON object")
        rows.append(row)
    return rows


def aggregate_season(
    manifest: dict[str, Any], rows: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    """Validate result rows and calculate capability and reliability views.

    ``attempt`` names one of the fixed scored slots. An infrastructure-invalid
    run may be followed by one valid replacement in the same slot; every run
    remains in the ledger under a unique ``run_id``. More than one valid row in
    a slot is rejected so a poor result can never be silently rerun.
    """

    _validate_manifest(manifest)
    season_id = manifest["season_id"]
    attempts = manifest["attempts_per_task"]
    task_ids = [task["id"] for task in manifest["tasks"]]
    harness_ids = [harness["id"] for harness in manifest["contenders"]]
    known_tasks = set(task_ids)
    known_harnesses = set(harness_ids)
    seen_runs: set[str] = set()
    cells: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)

    for index, original in enumerate(rows, start=1):
        row = _validate_result_row(original, index, season_id, attempts)
        if row["task_id"] not in known_tasks:
            raise SeasonError(f"unknown task_id on result line {index}: {row['task_id']}")
        if row["harness_id"] not in known_harnesses:
            raise SeasonError(
                f"unknown harness_id on result line {index}: {row['harness_id']}"
            )
        if row["run_id"] in seen_runs:
            raise SeasonError(f"duplicate run_id: {row['run_id']}")
        seen_runs.add(row["run_id"])
        key = (row["harness_id"], row["task_id"], row["attempt"])
        cells[key].append(row)

    contenders: list[dict[str, Any]] = []
    for harness_id in harness_ids:
        valid_by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
        invalid_count = 0
        missing_valid_slots: list[str] = []
        for task_id in task_ids:
            for attempt in range(1, attempts + 1):
                slot = cells.get((harness_id, task_id, attempt), [])
                valid = [row for row in slot if row["qualification"] == "valid"]
                invalid_count += sum(
                    row["qualification"] == "invalid" for row in slot
                )
                if len(valid) > 1:
                    raise SeasonError(
                        f"multiple valid results for {harness_id}/{task_id}/attempt-{attempt}"
                    )
                if valid:
                    valid_by_task[task_id].append(valid[0])
                else:
                    missing_valid_slots.append(f"{task_id}/attempt-{attempt}")

        valid_rows = [
            row for task_id in task_ids for row in valid_by_task.get(task_id, [])
        ]
        scores = [row["outcome_score"] for row in valid_rows]
        elapsed = [
            row["elapsed_seconds"]
            for row in valid_rows
            if row.get("elapsed_seconds") is not None
        ]
        task_best: dict[str, float] = {
            task_id: max(row["outcome_score"] for row in task_rows)
            for task_id, task_rows in valid_by_task.items()
            if task_rows
        }
        task_worst: dict[str, float] = {
            task_id: min(row["outcome_score"] for row in task_rows)
            for task_id, task_rows in valid_by_task.items()
            if task_rows
        }
        task_mean: dict[str, float] = {
            task_id: statistics.fmean(
                row["outcome_score"] for row in valid_by_task.get(task_id, [])
            )
            for task_id in task_ids
            if valid_by_task.get(task_id)
        }
        task_ranges = [
            task_best[task_id] - task_worst[task_id] for task_id in task_best
        ]
        complete = not missing_valid_slots
        primary = manifest["scoring"]["primary"]
        overall_outcome = (
            _mean(task_best.values())
            if primary == "mean_of_per_task_best_valid_outcome"
            else _mean(task_mean.values())
        )
        metrics = {
            "overall_outcome": overall_outcome,
            "best_outcome": _mean(task_best.values()),
            "mean_outcome": _mean(scores),
            "median_outcome": statistics.median(scores) if scores else None,
            "per_task_worst_outcome": _mean(task_worst.values()),
            "full_credit_rate": _rate(scores, lambda value: value == 1.0),
            "zero_score_rate": _rate(scores, lambda value: value == 0.0),
            "attempt_score_stddev": statistics.pstdev(scores)
            if len(scores) > 1
            else (0.0 if scores else None),
            "mean_within_task_range": _mean(task_ranges),
            "median_elapsed_seconds": statistics.median(elapsed) if elapsed else None,
            "intervention_count": sum(
                row.get("intervention_count", 0) for row in valid_rows
            ),
        }
        contenders.append(
            {
                "harness_id": harness_id,
                "complete": complete,
                "ranking_eligible": complete,
                "valid_result_count": len(valid_rows),
                "expected_valid_result_count": len(task_ids) * attempts,
                "invalid_attempt_count": invalid_count,
                "missing_valid_slots": missing_valid_slots,
                "metrics": _rounded(metrics),
                "per_task": {
                    task_id: {
                        "valid_attempts": len(valid_by_task.get(task_id, [])),
                        "best": task_best.get(task_id),
                        "mean": task_mean.get(task_id),
                        "worst": task_worst.get(task_id),
                    }
                    for task_id in task_ids
                },
            }
        )

    eligible = [row for row in contenders if row["ranking_eligible"]]
    eligible.sort(key=_rank_key)
    ranks = {row["harness_id"]: index for index, row in enumerate(eligible, 1)}
    for contender in contenders:
        contender["rank"] = ranks.get(contender["harness_id"])
    contenders.sort(
        key=lambda row: (
            row["rank"] is None,
            row["rank"] if row["rank"] is not None else math.inf,
            row["harness_id"],
        )
    )
    return {
        "schema_version": 1,
        "season_id": season_id,
        "pack_id": manifest["pack_id"],
        "status": "complete" if len(eligible) == len(harness_ids) else "provisional",
        "ranking_contract": manifest["scoring"],
        "contenders": contenders,
    }


def leaderboard_markdown(summary: dict[str, Any]) -> str:
    primary = summary["ranking_contract"]["primary"]
    lines = [
        f"# {summary['season_id']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "| Rank | Harness | Overall | Best/task | Mean | Median | Worst/task | Zero | Stddev | Invalid | Valid |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["contenders"]:
        metrics = row["metrics"]
        lines.append(
            "| {rank} | {harness} | {overall} | {best} | {mean} | {median} | {worst} | "
            "{zero} | {stddev} | {invalid} | {valid}/{expected} |".format(
                rank=row["rank"] if row["rank"] is not None else "—",
                harness=row["harness_id"],
                overall=_format(metrics["overall_outcome"]),
                best=_format(metrics["best_outcome"]),
                mean=_format(metrics["mean_outcome"]),
                median=_format(metrics["median_outcome"]),
                worst=_format(metrics["per_task_worst_outcome"]),
                zero=_format(metrics["zero_score_rate"]),
                stddev=_format(metrics["attempt_score_stddev"]),
                invalid=row["invalid_attempt_count"],
                valid=row["valid_result_count"],
                expected=row["expected_valid_result_count"],
            )
        )
    lines.extend(
        [
            "",
            f"Overall follows the frozen primary rule `{primary}`. Incomplete contenders are shown but never ranked.",
            "",
            "## Per-task outcome scores",
            "",
            "Each cell is the task mean followed by the worst–best attempt range. A single value means all valid attempts matched.",
            "",
        ]
    )
    harnesses = [row["harness_id"] for row in summary["contenders"]]
    task_ids = list(summary["contenders"][0]["per_task"])
    lines.append("| Task | " + " | ".join(harnesses) + " |")
    lines.append("|---|" + "---:|" * len(harnesses))
    rows_by_harness = {
        row["harness_id"]: row["per_task"] for row in summary["contenders"]
    }
    for task_id in task_ids:
        cells = [
            _format_task_score(rows_by_harness[harness_id][task_id])
            for harness_id in harnesses
        ]
        lines.append(f"| {task_id} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _validate_manifest(manifest: Any) -> None:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise SeasonError("season manifest must be a schema_version 1 object")
    for field in ("season_id", "pack_id"):
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            raise SeasonError(f"season manifest requires {field}")
    attempts = manifest.get("attempts_per_task")
    if not isinstance(attempts, int) or not 1 <= attempts <= 20:
        raise SeasonError("attempts_per_task must be an integer from 1 to 20")
    for field in ("tasks", "contenders"):
        values = manifest.get(field)
        if not isinstance(values, list) or not values:
            raise SeasonError(f"season manifest requires a non-empty {field} list")
        ids = [item.get("id") for item in values if isinstance(item, dict)]
        if len(ids) != len(values) or any(not isinstance(value, str) for value in ids):
            raise SeasonError(f"every {field} entry requires a string id")
        if len(set(ids)) != len(ids):
            raise SeasonError(f"duplicate id in season {field}")
    scoring = manifest.get("scoring")
    supported_primary = {
        "mean_of_per_task_best_valid_outcome",
        "mean_of_per_task_mean_valid_outcome",
    }
    if not isinstance(scoring, dict) or scoring.get("primary") not in supported_primary:
        raise SeasonError("unsupported or missing season scoring contract")


def _validate_result_row(
    original: dict[str, Any], index: int, season_id: str, attempts: int
) -> dict[str, Any]:
    row = dict(original)
    required_text = ("run_id", "season_id", "task_id", "harness_id", "qualification")
    for field in required_text:
        if not isinstance(row.get(field), str) or not row[field]:
            raise SeasonError(f"result line {index} requires string {field}")
    if row["season_id"] != season_id:
        raise SeasonError(f"result line {index} belongs to a different season")
    attempt = row.get("attempt")
    if not isinstance(attempt, int) or not 1 <= attempt <= attempts:
        raise SeasonError(
            f"result line {index} attempt must be from 1 to {attempts}"
        )
    qualification = row["qualification"]
    if qualification not in {"valid", "invalid"}:
        raise SeasonError(f"result line {index} qualification must be valid or invalid")
    score = row.get("outcome_score")
    if qualification == "valid":
        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not 0 <= score <= 1
        ):
            raise SeasonError(
                f"valid result line {index} requires outcome_score from 0 to 1"
            )
        row["outcome_score"] = float(score)
    elif score is not None:
        raise SeasonError(f"invalid result line {index} cannot have outcome_score")
    elapsed = row.get("elapsed_seconds")
    if elapsed is not None and (
        not isinstance(elapsed, (int, float))
        or isinstance(elapsed, bool)
        or elapsed < 0
    ):
        raise SeasonError(f"result line {index} elapsed_seconds must be non-negative")
    interventions = row.get("intervention_count", 0)
    if not isinstance(interventions, int) or interventions < 0:
        raise SeasonError(f"result line {index} intervention_count must be non-negative")
    row["intervention_count"] = interventions
    return row


def _rank_key(row: dict[str, Any]) -> tuple[Any, ...]:
    metrics = row["metrics"]
    elapsed = metrics["median_elapsed_seconds"]
    return (
        -metrics["overall_outcome"],
        -metrics["best_outcome"],
        -metrics["mean_outcome"],
        metrics["zero_score_rate"],
        elapsed if elapsed is not None else math.inf,
        row["harness_id"],
    )


def _mean(values: Iterable[float]) -> float | None:
    materialized = list(values)
    return statistics.fmean(materialized) if materialized else None


def _rate(values: list[float], predicate: Any) -> float | None:
    return sum(predicate(value) for value in values) / len(values) if values else None


def _rounded(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _rounded(item) for key, item in value.items()}
    if isinstance(value, float):
        return round(value, 6)
    return value


def _format(value: float | None) -> str:
    return f"{value:.4f}" if value is not None else "—"


def _format_task_score(task: dict[str, Any]) -> str:
    mean = task["mean"]
    worst = task["worst"]
    best = task["best"]
    if mean is None or worst is None or best is None:
        return "—"
    if worst == best:
        return _format(mean)
    return f"{_format(mean)} ({_format(worst)}–{_format(best)})"

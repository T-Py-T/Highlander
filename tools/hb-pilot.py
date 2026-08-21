#!/usr/bin/env python3
"""Run a frozen Highlander host-isolated HarnessBench pilot."""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from highlander.hb_pilot import (
    aggregate_pilot,
    classify_harnessbench_result,
    verify_frozen_protocol,
)


AUTH_FAILURE_MARKERS = (
    "not logged in",
    "authentication required",
    "authentication failed",
    "unauthorized",
    "missing credential",
    "no credential",
    "please login",
    "please log in",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    execute = sub.add_parser("execute")
    execute.add_argument("--protocol", required=True, type=Path)
    execute.add_argument("--protocol-sha256", required=True, type=Path)
    execute.add_argument("--upstream", required=True, type=Path)
    execute.add_argument("--profile-root", required=True, type=Path)
    execute.add_argument("--output-root", default=ROOT / "results", type=Path)
    args = parser.parse_args()
    if args.command == "execute":
        return execute_pilot(
            args.protocol,
            args.protocol_sha256,
            args.upstream,
            args.profile_root,
            args.output_root,
        )
    return 64


def execute_pilot(
    protocol_path: Path,
    sidecar_path: Path,
    upstream: Path,
    profile_root: Path,
    output_root: Path,
) -> int:
    protocol_sha = verify_frozen_protocol(protocol_path, sidecar_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol_id = str(protocol["protocol_id"])
    upstream = upstream.resolve()
    profile_root = profile_root.resolve()
    run_dir = output_root.resolve() / protocol_id
    if run_dir.exists():
        raise SystemExit(f"refusing to overwrite existing pilot evidence: {run_dir}")
    _verify_protocol_inputs(protocol, upstream)
    run_dir.mkdir(parents=True)
    shutil.copy2(protocol_path, run_dir / "protocol.json")
    shutil.copy2(sidecar_path, run_dir / "protocol.json.sha256")

    harnesses = {row["id"]: row for row in protocol["harnesses"]}
    unavailable_lanes = {
        row["id"]: row.get("reason", "unavailable")
        for row in protocol.get("unavailable_harnesses", [])
    }
    for harness_id, harness in harnesses.items():
        for relative in harness.get("required_profile_files", []):
            if not (profile_root / relative).is_file():
                unavailable_lanes[harness_id] = "dedicated_auth_profile_unavailable"
                break

    start = {
        "schema_version": 1,
        "protocol_id": protocol_id,
        "protocol_sha256": protocol_sha,
        "started_at": _utc_now(),
        "upstream_commit": _git(upstream, "rev-parse", "HEAD"),
        "upstream_tree": _git(upstream, "rev-parse", "HEAD^{tree}"),
        "highlander_head": _git(ROOT, "rev-parse", "HEAD"),
        "profile_id": protocol["authentication"]["profile_id"],
        "credential_values_recorded": False,
        "initial_unavailable_lanes": unavailable_lanes,
    }
    _write_json(run_dir / "run-start.json", start)
    rows: list[dict[str, Any]] = []
    task_id = protocol["task"]["id"]
    timeout = int(protocol["limits"]["wall_time_seconds"])

    for schedule_row in protocol["trial_order"]:
        harness_id = str(schedule_row["harness_id"])
        attempt = int(schedule_row["attempt"])
        sequence = int(schedule_row["sequence"])
        trial_id = f"{sequence:03d}-{harness_id}-attempt-{attempt:03d}"
        trial_dir = run_dir / "trials" / trial_id
        trial_dir.mkdir(parents=True)
        if harness_id in unavailable_lanes:
            row = _unavailable_row(
                protocol_id,
                task_id,
                harness_id,
                attempt,
                sequence,
                unavailable_lanes[harness_id],
            )
            _write_json(trial_dir / "result.json", row)
            _write_manifest(trial_dir)
            rows.append(row)
            print(f"[highlander] {trial_id}: unavailable", flush=True)
            continue

        print(f"[highlander] {trial_id}: starting", flush=True)
        app_config = {
            "data_dir": str(trial_dir / "hb-data"),
            "tasks_dir": str(upstream / "tasks"),
            "default_timeout_sec": timeout,
            "default_rounds": 1,
            "results_dir": str(trial_dir / "hb-results"),
            "work_root": str(trial_dir / "hb-work"),
        }
        model_label = str(harnesses[harness_id]["configured_model_id"])
        harness_config = {
            "models": {
                harness_id: {
                    "adapter": "generic_cli",
                    "command": sys.executable,
                    "session_prefix": f"highlander-{harness_id}-a{attempt}",
                    "timeout_sec": timeout,
                    "model": model_label,
                    "args": [
                        str(ROOT / "tools" / "hb-host-adapter.py"),
                        "--harness",
                        harness_id,
                        "--workspace",
                        "{workspace}",
                        "--prompt-file",
                        "{prompt_file}",
                        "--evidence-dir",
                        "{sandbox}/highlander-native",
                        "--timeout-seconds",
                        str(timeout),
                    ],
                }
            }
        }
        control_dir = trial_dir / "control"
        control_dir.mkdir()
        app_path = control_dir / "app.json"
        harness_path = control_dir / "harness.json"
        _write_json(app_path, app_config)
        _write_json(harness_path, harness_config)
        _write_json(
            control_dir / "trial.json",
            {
                **schedule_row,
                "protocol_sha256": protocol_sha,
                "task_id": task_id,
                "configured_model_id": model_label,
                "reasoning": harnesses[harness_id]["reasoning"],
                "provider_route": harnesses[harness_id]["provider_route"],
                "operator_interventions": 0,
            },
        )
        env = os.environ.copy()
        env.update(
            {
                "PYTHONPATH": str(upstream / "src"),
                "HARNESSBENCH_APP_CONFIG": str(app_path),
                "HARNESSBENCH_HARNESS_CONFIG": str(harness_path),
                "HARNESSBENCH_SKIP_PROCESS_GRADE": "1",
                "HIGHLANDER_PILOT_PROFILE_ROOT": str(profile_root),
            }
        )
        command = [
            sys.executable,
            "-m",
            "harnessbench.cli",
            "run-task",
            "--task",
            task_id,
            "--harness",
            harness_id,
            "--mode",
            "live",
        ]
        started = dt.datetime.now(dt.timezone.utc)
        outer_timeout = timeout + 90
        try:
            completed = subprocess.run(
                command,
                cwd=upstream,
                env=env,
                capture_output=True,
                timeout=outer_timeout,
                check=False,
            )
            outer_returncode = completed.returncode
            outer_timed_out = False
            outer_stdout = completed.stdout
            outer_stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            outer_returncode = 124
            outer_timed_out = True
            outer_stdout = exc.stdout or b""
            outer_stderr = exc.stderr or b""
        (trial_dir / "controller.stdout.raw").write_bytes(outer_stdout)
        (trial_dir / "controller.stderr.raw").write_bytes(outer_stderr)
        outer_elapsed = round((dt.datetime.now(dt.timezone.utc) - started).total_seconds(), 3)

        upstream_results = list(
            (trial_dir / "hb-results").glob(f"{harness_id}/*/{task_id}.json")
        )
        native_execution_files = list(
            (trial_dir / "hb-work").rglob("highlander-native/execution.json")
        )
        if len(upstream_results) == 1:
            payload = json.loads(upstream_results[0].read_text(encoding="utf-8"))
            shutil.copy2(upstream_results[0], trial_dir / "upstream-result.json")
        else:
            payload = {"adapter_result": {"ok": False}}
        if len(native_execution_files) == 1:
            native_dir = native_execution_files[0].parent
            wrapper_execution = json.loads(
                native_execution_files[0].read_text(encoding="utf-8")
            )
            shutil.copytree(native_dir, trial_dir / "native")
        else:
            wrapper_execution = {"returncode": outer_returncode, "timed_out": outer_timed_out}

        classification = classify_harnessbench_result(
            payload, wrapper_execution=wrapper_execution
        )
        error_text = (outer_stdout + b"\n" + outer_stderr).decode(
            "utf-8", errors="replace"
        ).lower()
        if classification["qualification"] == "invalid" and any(
            marker in error_text for marker in AUTH_FAILURE_MARKERS
        ):
            classification["invalid_reason"] = "authentication_unavailable"
            unavailable_lanes[harness_id] = "authentication_unavailable_after_first_attempt"

        workspace_path = (
            Path(str(payload.get("workspace", "")))
            if payload.get("workspace")
            else None
        )
        if workspace_path and workspace_path.is_dir():
            final_workspace = trial_dir / "workspace-final"
            shutil.copytree(workspace_path, final_workspace)
            _write_fixture_diff(
                upstream / "tasks" / task_id / str(protocol["task"]["fixtures_dir"]),
                final_workspace,
                trial_dir / "diff.patch",
            )
        else:
            final_workspace = None

        metrics = wrapper_execution.get("process_metrics", {})
        event_count = metrics.get("event_count") if isinstance(metrics, dict) else None
        tool_event_count = metrics.get("tool_event_count") if isinstance(metrics, dict) else None
        if harness_id == "hermes" or not event_count:
            tool_event_count = None
        usage = (
            payload.get("usage_summary")
            if isinstance(payload.get("usage_summary"), dict)
            else {}
        )
        control_proof = _control_proof(harnesses[harness_id], payload, trial_dir / "native")
        _write_json(trial_dir / "control-proof.json", control_proof)
        row = {
            "schema_version": 1,
            "protocol_id": protocol_id,
            "protocol_sha256": protocol_sha,
            "task_id": task_id,
            "harness_id": harness_id,
            "attempt": attempt,
            "sequence": sequence,
            **classification,
            "elapsed_seconds": wrapper_execution.get("elapsed_seconds", outer_elapsed),
            "outer_elapsed_seconds": outer_elapsed,
            "tool_event_count": tool_event_count,
            "event_count": event_count,
            "operator_interventions": 0,
            "usage": usage,
            "control_proof": control_proof,
            "artifacts": {
                "trial": f"trials/{trial_id}",
                "native": f"trials/{trial_id}/native" if (trial_dir / "native").is_dir() else None,
                "upstream_result": f"trials/{trial_id}/upstream-result.json" if (trial_dir / "upstream-result.json").is_file() else None,
                "final_workspace": f"trials/{trial_id}/workspace-final" if final_workspace else None,
                "diff": f"trials/{trial_id}/diff.patch" if (trial_dir / "diff.patch").is_file() else None,
            },
        }
        _write_json(trial_dir / "result.json", row)
        cleanup_targets = [
            trial_dir / "hb-work",
            trial_dir / "hb-results",
            trial_dir / "hb-data",
        ]
        for target in cleanup_targets:
            shutil.rmtree(target, ignore_errors=True)
        _write_json(
            trial_dir / "cleanup.json",
            {
                "sandbox_removed": not (trial_dir / "hb-work").exists(),
                "temporary_results_removed": not (trial_dir / "hb-results").exists(),
                "temporary_data_removed": not (trial_dir / "hb-data").exists(),
                "final_workspace_retained": bool(final_workspace),
                "auth_profile_removed": False,
                "auth_profile_policy": "dedicated host profile retained for subscription refresh",
            },
        )
        _write_manifest(trial_dir)
        rows.append(row)
        print(f"[highlander] {trial_id}: {row['qualification']} outcome={row['outcome_score']}", flush=True)

    # Record lanes omitted from the paid schedule (for example NanoBot) as unavailable,
    # without manufacturing attempt slots or zero scores.
    for item in protocol.get("unavailable_harnesses", []):
        if not any(row["harness_id"] == item["id"] for row in rows):
            rows.append(
                _unavailable_row(
                    protocol_id,
                    task_id,
                    str(item["id"]),
                    0,
                    0,
                    str(item.get("reason", "unavailable")),
                )
            )
    summary = aggregate_pilot(rows, expected_attempts=int(protocol["attempts_per_harness_task"]))
    summary.update(
        {
            "schema_version": 1,
            "protocol_id": protocol_id,
            "protocol_sha256": protocol_sha,
            "task_id": task_id,
            "completed_at": _utc_now(),
            "trial_rows": rows,
            "claim_boundary": protocol["claim_boundary"],
        }
    )
    _write_json(run_dir / "summary.json", summary)
    _write_report(run_dir / "report.md", protocol, summary)
    _write_manifest(run_dir)
    print(f"[highlander] complete: {run_dir}", flush=True)
    return 0


def _verify_protocol_inputs(protocol: dict[str, Any], upstream: Path) -> None:
    expected_upstream = protocol["upstream"]
    observed_commit = _git(upstream, "rev-parse", "HEAD")
    observed_tree = _git(upstream, "rev-parse", "HEAD^{tree}")
    if observed_commit != expected_upstream["commit"] or observed_tree != expected_upstream["tree"]:
        raise ValueError("upstream HarnessBench commit/tree drifted from protocol")
    for relative, expected in protocol["source_hashes"].items():
        path = ROOT / relative
        if _sha256(path) != expected:
            raise ValueError(f"Highlander runner source drifted: {relative}")
    task_dir = upstream / "tasks" / protocol["task"]["id"]
    for relative, expected in protocol["task"]["file_hashes"].items():
        if _sha256(task_dir / relative) != expected:
            raise ValueError(f"HarnessBench task input drifted: {relative}")
    outcome_scoring = protocol["scoring"]["outcome"]
    oracle = upstream / outcome_scoring["oracle_path"]
    if _sha256(oracle) != outcome_scoring["oracle_sha256"]:
        raise ValueError("deterministic oracle drifted from protocol")


def _unavailable_row(
    protocol_id: str,
    task_id: str,
    harness_id: str,
    attempt: int,
    sequence: int,
    reason: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "protocol_id": protocol_id,
        "task_id": task_id,
        "harness_id": harness_id,
        "attempt": attempt,
        "sequence": sequence,
        "qualification": "unavailable",
        "invalid_reason": reason,
        "outcome_score": None,
        "process_status": "not_evaluated",
        "process_score": None,
        "combined_score": None,
        "elapsed_seconds": None,
        "tool_event_count": None,
        "operator_interventions": 0,
    }


def _control_proof(harness: dict[str, Any], payload: dict[str, Any], native_dir: Path) -> dict[str, Any]:
    observations: dict[str, set[str]] = {
        "model": set(),
        "provider": set(),
        "reasoning": set(),
    }
    candidates: list[Any] = [payload.get("usage_summary"), payload.get("adapter_results")]
    usage_file = native_dir / "usage.json"
    if usage_file.is_file():
        try:
            candidates.append(json.loads(usage_file.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    for candidate in candidates:
        _collect_named_values(candidate, observations)
    return {
        "configured_model_id": harness["configured_model_id"],
        "provider_route": harness["provider_route"],
        "reasoning": harness["reasoning"],
        "fallback_policy": "forbidden",
        "observed": {key: sorted(values) for key, values in observations.items()},
        "configured_verified": True,
        "runtime_observation_available": any(observations.values()),
        "provider_wire_verified": False,
        "qualification_boundary": "host-isolated subscription-realism; exact wire proof unavailable",
    }


def _collect_named_values(value: Any, output: dict[str, set[str]]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("_", "")
            if isinstance(child, (str, int, float)):
                if normalized in {"model", "modelid", "responsemodel"}:
                    output["model"].add(str(child))
                elif normalized in {"provider", "providerid", "billingprovider"}:
                    output["provider"].add(str(child))
                elif normalized in {"reasoning", "effort", "variant"}:
                    output["reasoning"].add(str(child))
            _collect_named_values(child, output)
    elif isinstance(value, list):
        for child in value:
            _collect_named_values(child, output)


def _write_fixture_diff(base: Path, final: Path, output: Path) -> None:
    chunks: list[str] = []
    relatives = sorted(
        {path.relative_to(base) for path in base.rglob("*") if path.is_file()}
        | {path.relative_to(final) for path in final.rglob("*") if path.is_file()}
    )
    for relative in relatives:
        left = base / relative
        right = final / relative
        left_bytes = left.read_bytes() if left.is_file() else b""
        right_bytes = right.read_bytes() if right.is_file() else b""
        if left_bytes == right_bytes:
            continue
        try:
            left_lines = left_bytes.decode("utf-8").splitlines(keepends=True)
            right_lines = right_bytes.decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            chunks.append(
                f"Binary files a/{relative.as_posix()} and b/{relative.as_posix()} differ "
                f"({_sha256_bytes(left_bytes)} -> {_sha256_bytes(right_bytes)})\n"
            )
            continue
        chunks.extend(
            difflib.unified_diff(
                left_lines,
                right_lines,
                fromfile=f"a/{relative.as_posix()}",
                tofile=f"b/{relative.as_posix()}",
            )
        )
    output.write_text("".join(chunks), encoding="utf-8")


def _write_report(path: Path, protocol: dict[str, Any], summary: dict[str, Any]) -> None:
    lines = [
        f"# {protocol['protocol_id']}",
        "",
        f"Protocol SHA-256: `{summary['protocol_sha256']}`",
        "",
        "This is a host-isolated, single-task subscription-realism pilot. It does not declare a winner.",
        "Process scoring and combined scoring were not evaluated.",
        "",
        "| Harness | Valid | Invalid | Unavailable | Mean outcome | Population σ | Mean seconds | Tool events |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["harnesses"]:
        lines.append(
            f"| {row['harness_id']} | {row['valid_trials']} | {row['invalid_trials']} | "
            f"{row['unavailable_trials']} | {_cell(row['mean_outcome'])} | "
            f"{_cell(row['population_stddev'])} | {_cell(row['mean_elapsed_seconds'])} | "
            f"{_cell(row['total_tool_events'])} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_manifest(root: Path) -> None:
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name == "artifact-manifest.json":
            continue
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    _write_json(
        root / "artifact-manifest.json",
        {"schema_version": 1, "generated_at": _utc_now(), "files": files},
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _cell(value: object) -> str:
    return "—" if value is None else str(value)


if __name__ == "__main__":
    raise SystemExit(main())

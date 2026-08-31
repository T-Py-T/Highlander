"""Frozen, resumable HarnessBench season execution in disposable containers."""

from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .cleanroom import CleanRoom
from .hb_clean import SUPPORTED_HARNESSES, execute_clean_adapter
from .hb_pilot import classify_harnessbench_result, verify_frozen_protocol
from .season import aggregate_season, leaderboard_markdown


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

SOURCE_FILES = (
    "highlander/cleanroom.py",
    "highlander/hb_clean.py",
    "highlander/hb_season_run.py",
    "highlander/season.py",
    "tools/hb-clean-adapter.py",
    "tools/hb-season.py",
)

LANE_CONTROLS: dict[str, dict[str, str]] = {
    "omp": {
        "configured_model_id": "openai-codex/gpt-5.6-luna",
        "provider_id": "openai-codex",
        "expected_runtime_model_id": "gpt-5.6-luna",
        "expected_runtime_provider_id": "openai-codex",
    },
    "opencode": {
        "configured_model_id": "openai/gpt-5.6-luna",
        "provider_id": "openai",
        "expected_runtime_model_id": "gpt-5.6-luna",
        "expected_runtime_provider_id": "openai",
    },
    "codex": {
        "configured_model_id": "gpt-5.6-luna",
        "provider_id": "openai-codex",
        "expected_runtime_model_id": "gpt-5.6-luna",
        "expected_runtime_provider_id": "openai-codex",
    },
    "hermes": {
        "configured_model_id": "gpt-5.6-luna",
        "provider_id": "openai-codex",
        "expected_runtime_model_id": "gpt-5.6-luna",
        "expected_runtime_provider_id": "openai-codex",
    },
    "atomic": {
        "configured_model_id": "gpt-5.6-luna",
        "provider_id": "openai-codex",
        "expected_runtime_model_id": "gpt-5.6-luna",
        "expected_runtime_provider_id": "openai-codex",
    },
    "nanobot": {
        "configured_model_id": "openai-codex/gpt-5.6-luna",
        "provider_id": "openai-codex",
        "expected_runtime_model_id": "gpt-5.6-luna",
        "expected_runtime_provider_id": "openai-codex",
    },
}


def freeze_protocol(
    *,
    root: Path,
    manifest_path: Path,
    upstream: Path,
    image_lock_path: Path,
    output: Path,
    schedule_seed: int = 56001,
) -> dict[str, Any]:
    """Freeze every executable input before route qualification or scoring calls."""

    root = root.resolve()
    manifest_path = manifest_path.resolve()
    upstream = upstream.resolve()
    output = output.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    image_lock = json.loads(image_lock_path.resolve().read_text(encoding="utf-8"))
    task_ids = [str(item["id"]) for item in manifest["tasks"]]
    contender_ids = [str(item["id"]) for item in manifest["contenders"]]
    if set(contender_ids) != set(SUPPORTED_HARNESSES):
        raise ValueError("season contenders must be the six supported clean harnesses")
    images = {name: str(item["image_id"]) for name, item in image_lock["images"].items()}
    if not set((*SUPPORTED_HARNESSES, "evaluator")) <= set(images):
        raise ValueError("image lock does not contain all season images")

    tasks = []
    for task in manifest["tasks"]:
        task_id = str(task["id"])
        task_dir = upstream / "tasks" / task_id
        files = {
            path.relative_to(task_dir).as_posix(): _sha256(path.read_bytes())
            for path in _files_below(task_dir)
        }
        tasks.append({**task, "file_hashes": files, "oracle_sha256": files["oracle_grade.py"]})

    versions = {str(item["id"]): str(item["version"]) for item in manifest["contenders"]}
    harnesses = []
    for harness_id in contender_ids:
        harnesses.append(
            {
                "id": harness_id,
                "version": versions[harness_id],
                **LANE_CONTROLS[harness_id],
                "reasoning": "medium",
                "wire_reasoning": "medium",
                "seed_profile": f"{harness_id}-subscription",
                "configuration_profile": "clean-core",
                "fallback_policy": "forbidden",
                "role": next(
                    str(row["role"])
                    for row in manifest["contenders"]
                    if row["id"] == harness_id
                ),
            }
        )

    stages = list(manifest["execution_stages"])
    ordered_tasks = [task_id for stage in stages for task_id in stage["task_ids"]]
    if ordered_tasks != task_ids:
        raise ValueError("manifest task order must match its execution stages")
    schedule = _schedule(
        task_ids,
        contender_ids,
        attempts=int(manifest["attempts_per_task"]),
        seed=schedule_seed,
    )
    protocol = {
        "schema_version": 1,
        "protocol_id": manifest["season_id"],
        "created_at": _utc_now(),
        "lane": "oci_clean_core_subscription_realism",
        "purpose": "Same-model hard coding and DevOps comparison using unchanged HarnessBench tasks and deterministic oracles.",
        "claim_boundary": (
            "HarnessBench outcome comparison under frozen configured subscription routes. "
            "Native runtime and wire identity are reported when exposed; absence of wire proof "
            "is not represented as proof. NanoBot is a version-pinned temporal proxy."
        ),
        "runner": {
            "repository": "https://github.com/T-Py-T/Highlander",
            "implementation_commit": _git(root, "rev-parse", "HEAD"),
            "implementation_tree": _git(root, "rev-parse", "HEAD^{tree}"),
        },
        "source_hashes": {
            relative: _sha256((root / relative).read_bytes()) for relative in SOURCE_FILES
        },
        "manifest": {
            "path": manifest_path.relative_to(root).as_posix(),
            "sha256": _sha256(manifest_path.read_bytes()),
            "pack_id": manifest["pack_id"],
            "scoring": manifest["scoring"],
        },
        "upstream": {
            "repository": manifest["upstream"]["repository"],
            "commit": _git(upstream, "rev-parse", "HEAD"),
            "tree": _git(upstream, "rev-parse", "HEAD^{tree}"),
            "task_files_modified": False,
        },
        "tasks": tasks,
        "harnesses": harnesses,
        "attempts_per_task": int(manifest["attempts_per_task"]),
        "execution_stages": stages,
        "trial_order_policy": {
            "type": "seeded_randomized_matched_blocks_within_each_task",
            "seed": schedule_seed,
            "parallelism": 1,
        },
        "trial_order": schedule,
        "runtime": {
            "oci": "podman",
            "profile": "clean-core",
            "network": "bridge",
            "cpus": 2.0,
            "memory_mb": 4096,
            "pids_limit": 512,
            "tmpfs_mb": 1024,
            "images": images,
            "host_home_mounted": False,
            "publication_credentials_available": False,
        },
        "permissions": {
            "workspace": "one fresh HarnessBench sandbox per trial",
            "tools": "native shipped harness tools are the treatment",
            "network": "provider route available; benchmark tasks require no external service",
            "memory_plugins_rules_mcp": "personal state absent or disabled",
            "publication": "no GitHub, SSH, or host publication credentials in workers",
            "operator_intervention": "none after each staged launch",
        },
        "limits": {
            "harness_wall_time_seconds": 1200,
            "controller_grace_seconds": 90,
            "common_token_cap": None,
            "common_cost_cap": None,
            "scheduled_scored_calls": len(schedule),
            "scheduled_qualification_calls": len(contender_ids),
        },
        "scoring": {
            "outcome": "unchanged deterministic HarnessBench oracle",
            "process": {"status": "not_evaluated", "judge": None, "score": None},
            "combined": {"status": "not_computed", "score": None},
            "ranking": manifest["scoring"],
        },
        "invalidation_and_disqualification": {
            "invalid_trial": [
                "authentication or model-route failure",
                "harness nonzero exit or timeout",
                "missing deterministic oracle result",
                "task, oracle, image, source, manifest, protocol, or upstream drift",
                "observed model/provider/reasoning conflicts with the frozen control",
            ],
            "valid_low_score_policy": "A deterministic outcome, including zero, is valid and never retried for performance.",
            "invalid_score_policy": "Invalid and unavailable runs have null scores and are never converted to zero.",
            "replacement_retry_policy": "No automatic retries; an infrastructure-invalid replacement must be explicitly recorded under the same scored slot.",
            "fallback_policy": "forbidden",
        },
        "qualification": {
            "prompt": "This is a model-route qualification. Use no tools. Reply exactly HIGHLANDER_ROUTE_OK.",
            "calls_per_harness": 1,
            "required_before_scored_run": True,
            "configured_route_is_not_wire_proof": True,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output, protocol)
    digest = _sha256(output.read_bytes())
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.name}\n", encoding="utf-8"
    )
    return {"protocol_id": protocol["protocol_id"], "sha256": digest, "calls": len(schedule)}


def doctor(protocol_path: Path, sidecar_path: Path, upstream: Path, root: Path) -> dict[str, Any]:
    protocol_sha = verify_frozen_protocol(protocol_path, sidecar_path)
    protocol = json.loads(protocol_path.resolve().read_text(encoding="utf-8"))
    _verify_inputs(protocol, upstream.resolve(), root.resolve())
    runtime = protocol["runtime"]
    room = CleanRoom({
        "runtime": runtime["oci"],
        "profile": runtime["profile"],
        "network": runtime["network"],
        "cpus": runtime["cpus"],
        "memory_mb": runtime["memory_mb"],
        "pids_limit": runtime["pids_limit"],
        "tmpfs_mb": runtime["tmpfs_mb"],
        "evaluator_image": runtime["images"]["evaluator"],
    })
    lanes = []
    for lane in protocol["harnesses"]:
        plan = room.plan_trial(
            match_id="hb-season-doctor",
            contender_id=str(lane["id"]),
            adapter=str(lane["id"]),
            image=runtime["images"][lane["id"]],
            seed_profile=str(lane["seed_profile"]),
            authentication_required=True,
        )
        lanes.append({
            "harness_id": lane["id"],
            "version": lane["version"],
            "image_id": plan["image_id"],
            "image_verified": plan["digest_verified"],
            "seed_profile": lane["seed_profile"],
            "seed_available": plan["seed"]["available"],
            "configured_model_id": lane["configured_model_id"],
        })
    return {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol_sha,
        "ready_for_qualification": all(row["seed_available"] for row in lanes),
        "lanes": lanes,
    }


def qualify(
    protocol_path: Path,
    sidecar_path: Path,
    upstream: Path,
    root: Path,
    output_root: Path,
) -> dict[str, Any]:
    status = doctor(protocol_path, sidecar_path, upstream, root)
    if not status["ready_for_qualification"]:
        raise ValueError("all six isolated auth seeds are required before qualification")
    protocol = json.loads(protocol_path.resolve().read_text(encoding="utf-8"))
    protocol_sha = str(status["protocol_sha256"])
    destination = output_root.resolve() / str(protocol["protocol_id"])
    if destination.exists():
        raise ValueError(f"qualification evidence is immutable: {destination}")
    destination.mkdir(parents=True)
    shutil.copy2(protocol_path, destination / "protocol.json")
    shutil.copy2(sidecar_path, destination / "protocol.json.sha256")
    rows = []
    for sequence, lane in enumerate(protocol["harnesses"], 1):
        harness_id = str(lane["id"])
        trial_id = f"qualification-{sequence:02d}-{harness_id}"
        trial_dir = destination / "trials" / trial_id
        with tempfile.TemporaryDirectory(prefix=f"highlander-{harness_id}-") as temporary:
            workspace = Path(temporary) / "workspace"
            workspace.mkdir()
            prompt = Path(temporary) / "prompt.txt"
            prompt.write_text(str(protocol["qualification"]["prompt"]), encoding="utf-8")
            native = trial_dir / "native"
            try:
                returncode = execute_clean_adapter(
                    protocol=protocol,
                    harness_id=harness_id,
                    workspace=workspace,
                    prompt_file=prompt,
                    evidence_dir=native,
                    trial_id=trial_id,
                )
                output = (native / "stdout.raw").read_text(encoding="utf-8", errors="replace")
                proof = _load_json(native / "control-proof.json")
                qualified = returncode == 0 and "HIGHLANDER_ROUTE_OK" in output
                reason = None if qualified else ("nonzero_exit" if returncode else "expected_reply_missing")
            except Exception as exc:
                qualified = False
                reason = f"qualification_infrastructure_error:{type(exc).__name__}"
                _write_json(trial_dir / "error.json", {"type": type(exc).__name__, "message": str(exc)})
                proof = None
            row = {
                "sequence": sequence,
                "harness_id": harness_id,
                "status": "qualified" if qualified else "unavailable",
                "reason": reason,
                "protocol_sha256": protocol_sha,
                "control_proof": proof,
                "artifact_path": f"trials/{trial_id}",
            }
            _write_json(trial_dir / "result.json", row)
            _write_manifest(trial_dir)
            rows.append(row)
    summary = {
        "schema_version": 1,
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol_sha,
        "completed_at": _utc_now(),
        "ready_for_scored_run": all(row["status"] == "qualified" for row in rows),
        "rows": rows,
        "model_calls": len(rows),
        "process_score": None,
        "combined_score": None,
    }
    _write_json(destination / "summary.json", summary)
    _write_manifest(destination)
    return summary


def execute_stage(
    *,
    protocol_path: Path,
    sidecar_path: Path,
    manifest_path: Path,
    upstream: Path,
    root: Path,
    qualification_root: Path,
    output_root: Path,
    stage_id: str | None,
    max_trials: int | None = None,
    retry_invalid: bool = False,
) -> dict[str, Any]:
    status = doctor(protocol_path, sidecar_path, upstream, root)
    protocol_sha = str(status["protocol_sha256"])
    protocol = json.loads(protocol_path.resolve().read_text(encoding="utf-8"))
    qualification = _load_json(
        qualification_root.resolve() / str(protocol["protocol_id"]) / "summary.json"
    )
    if qualification.get("protocol_sha256") != protocol_sha or not qualification.get(
        "ready_for_scored_run"
    ):
        raise ValueError("a complete qualification for this exact protocol is required")
    manifest = json.loads(manifest_path.resolve().read_text(encoding="utf-8"))
    run_dir = output_root.resolve() / f"{protocol['protocol_id']}-raw"
    run_dir.mkdir(parents=True, exist_ok=True)
    _ensure_frozen_copy(protocol_path, run_dir / "protocol.json")
    _ensure_frozen_copy(sidecar_path, run_dir / "protocol.json.sha256")
    _ensure_frozen_copy(manifest_path, run_dir / "season-manifest.json")
    qualification_source = qualification_root.resolve() / str(protocol["protocol_id"])
    qualification_manifest = qualification_source / "artifact-manifest.json"
    _ensure_frozen_copy(qualification_manifest, run_dir / "qualification-artifact-manifest.json")
    qualification_copy = run_dir / "qualification"
    if not qualification_copy.exists():
        shutil.copytree(qualification_source, qualification_copy)
    elif (qualification_copy / "artifact-manifest.json").read_bytes() != qualification_manifest.read_bytes():
        raise ValueError("retained qualification evidence changed")

    existing = _existing_results(run_dir)
    completed_slots = {
        (row["task_id"], row["harness_id"], int(row["attempt"]))
        for row in existing
        if row["qualification"] == "valid"
    }
    attempted_slots = {
        (row["task_id"], row["harness_id"], int(row["attempt"])) for row in existing
    }
    unavailable_harnesses = {
        str(row["harness_id"])
        for row in existing
        if row.get("invalid_reason") == "authentication_unavailable"
    }
    selected_tasks = _stage_tasks(protocol, stage_id)
    schedule = [row for row in protocol["trial_order"] if row["task_id"] in selected_tasks]
    launched = 0
    for scheduled in schedule:
        slot = (scheduled["task_id"], scheduled["harness_id"], int(scheduled["attempt"]))
        if slot in completed_slots:
            continue
        if slot in attempted_slots and not retry_invalid:
            continue
        if scheduled["harness_id"] in unavailable_harnesses:
            continue
        if max_trials is not None and launched >= max_trials:
            break
        row = _execute_trial(
            protocol=protocol,
            protocol_sha=protocol_sha,
            scheduled=scheduled,
            upstream=upstream.resolve(),
            root=root.resolve(),
            run_dir=run_dir,
        )
        existing.append(row)
        attempted_slots.add(slot)
        _append_jsonl(run_dir / "results.jsonl", row)
        if row["qualification"] == "valid":
            completed_slots.add(slot)
        elif row.get("invalid_reason") == "authentication_unavailable":
            unavailable_harnesses.add(str(row["harness_id"]))
        launched += 1
        _write_season_summary(run_dir, protocol, manifest, existing, stage_id)
    summary = _write_season_summary(run_dir, protocol, manifest, existing, stage_id)
    _write_manifest(run_dir)
    return summary


def _execute_trial(
    *,
    protocol: dict[str, Any],
    protocol_sha: str,
    scheduled: dict[str, Any],
    upstream: Path,
    root: Path,
    run_dir: Path,
) -> dict[str, Any]:
    task_id = str(scheduled["task_id"])
    harness_id = str(scheduled["harness_id"])
    attempt = int(scheduled["attempt"])
    sequence = int(scheduled["sequence"])
    prior = len(list((run_dir / "trials").glob(f"*-{task_id}-{harness_id}-a{attempt:02d}-r*")))
    retry = prior + 1
    trial_id = f"{sequence:03d}-{task_id}-{harness_id}-a{attempt:02d}-r{retry:02d}"
    trial_dir = run_dir / "trials" / trial_id
    trial_dir.mkdir(parents=True)
    lane = next(row for row in protocol["harnesses"] if row["id"] == harness_id)
    timeout = int(protocol["limits"]["harness_wall_time_seconds"])
    control_dir = trial_dir / "control"
    control_dir.mkdir()
    app_path = control_dir / "app.json"
    harness_path = control_dir / "harness.json"
    _write_json(app_path, {
        "data_dir": str(trial_dir / "hb-data"),
        "tasks_dir": str(upstream / "tasks"),
        "default_timeout_sec": timeout,
        "default_rounds": 1,
        "results_dir": str(trial_dir / "hb-results"),
        "work_root": str(trial_dir / "hb-work"),
    })
    _write_json(harness_path, {"models": {harness_id: {
        "adapter": "generic_cli",
        "command": sys.executable,
        "session_prefix": f"highlander-{harness_id}-{task_id}-a{attempt}",
        "timeout_sec": timeout,
        "model": lane["configured_model_id"],
        "args": [
            str(root / "tools" / "hb-clean-adapter.py"),
            "--protocol", str(run_dir / "protocol.json"),
            "--harness", harness_id,
            "--workspace", "{workspace}",
            "--prompt-file", "{prompt_file}",
            "--evidence-dir", "{sandbox}/highlander-native",
            "--trial-id", trial_id,
        ],
    }}})
    _write_json(control_dir / "trial.json", {
        **scheduled,
        "retry": retry,
        "protocol_sha256": protocol_sha,
        "configured_model_id": lane["configured_model_id"],
        "provider_id": lane["provider_id"],
        "reasoning": lane["reasoning"],
        "operator_interventions": 0,
    })
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(upstream / "src"),
        "HARNESSBENCH_APP_CONFIG": str(app_path),
        "HARNESSBENCH_HARNESS_CONFIG": str(harness_path),
        "HARNESSBENCH_SKIP_PROCESS_GRADE": "1",
        "HARNESSBENCH_SKIP_ORACLE_QUALITY_LLM": "1",
    })
    command = [
        sys.executable, "-m", "harnessbench.cli", "run-task",
        "--task", task_id, "--harness", harness_id, "--mode", "live",
    ]
    started = dt.datetime.now(dt.timezone.utc)
    try:
        completed = subprocess.run(
            command,
            cwd=upstream,
            env=env,
            capture_output=True,
            timeout=timeout + int(protocol["limits"]["controller_grace_seconds"]),
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

    upstream_results = list((trial_dir / "hb-results").glob(f"{harness_id}/*/{task_id}.json"))
    native_executions = list((trial_dir / "hb-work").rglob("highlander-native/execution.json"))
    payload: dict[str, Any]
    if len(upstream_results) == 1:
        payload = _load_json(upstream_results[0])
        shutil.copy2(upstream_results[0], trial_dir / "upstream-result.json")
    else:
        payload = {"adapter_result": {"ok": False}}
    if len(native_executions) == 1:
        native_source = native_executions[0].parent
        wrapper_execution = _load_json(native_executions[0])
        shutil.copytree(native_source, trial_dir / "native")
    else:
        wrapper_execution = {"returncode": outer_returncode, "timed_out": outer_timed_out}
    classification = classify_harnessbench_result(payload, wrapper_execution=wrapper_execution)
    proof = (
        _load_json(trial_dir / "native" / "control-proof.json")
        if (trial_dir / "native" / "control-proof.json").is_file()
        else None
    )
    if (
        classification["qualification"] == "valid"
        and isinstance(proof, dict)
        and proof.get("runtime_observation_available")
        and not proof.get("runtime_verified")
    ):
        classification = {
            "qualification": "invalid",
            "invalid_reason": "observed_model_control_conflict",
            "outcome_score": None,
            "process_status": "not_evaluated",
            "process_score": None,
            "combined_score": None,
        }
    error_text = (outer_stdout + b"\n" + outer_stderr).decode("utf-8", errors="replace").lower()
    if classification["qualification"] == "invalid" and any(
        marker in error_text for marker in AUTH_FAILURE_MARKERS
    ):
        classification["invalid_reason"] = "authentication_unavailable"

    workspace = Path(str(payload.get("workspace", ""))) if payload.get("workspace") else None
    final_workspace = None
    if workspace and workspace.is_dir():
        final_workspace = trial_dir / "workspace-final"
        shutil.copytree(workspace, final_workspace)
        _write_fixture_diff(upstream / "tasks" / task_id / "fixtures", final_workspace, trial_dir / "diff.patch")
    row = {
        "schema_version": 1,
        "run_id": f"{protocol['protocol_id']}-{task_id}-{harness_id}-a{attempt:02d}-r{retry:02d}",
        "season_id": protocol["protocol_id"],
        "protocol_sha256": protocol_sha,
        "task_id": task_id,
        "harness_id": harness_id,
        "attempt": attempt,
        "retry": retry,
        "sequence": sequence,
        **classification,
        "elapsed_seconds": wrapper_execution.get("elapsed_seconds", outer_elapsed),
        "outer_elapsed_seconds": outer_elapsed,
        "intervention_count": 0,
        "control_proof": proof,
        "process_score": None,
        "combined_score": None,
        "artifact_path": f"trials/{trial_id}",
        "artifacts": {
            "native": f"trials/{trial_id}/native" if (trial_dir / "native").is_dir() else None,
            "upstream_result": f"trials/{trial_id}/upstream-result.json" if (trial_dir / "upstream-result.json").is_file() else None,
            "workspace": f"trials/{trial_id}/workspace-final" if final_workspace else None,
            "diff": f"trials/{trial_id}/diff.patch" if (trial_dir / "diff.patch").is_file() else None,
        },
    }
    _write_json(trial_dir / "result.json", row)
    for target in (trial_dir / "hb-work", trial_dir / "hb-results", trial_dir / "hb-data"):
        shutil.rmtree(target, ignore_errors=True)
    _write_json(trial_dir / "cleanup.json", {
        "sandbox_removed": not (trial_dir / "hb-work").exists(),
        "temporary_results_removed": not (trial_dir / "hb-results").exists(),
        "temporary_data_removed": not (trial_dir / "hb-data").exists(),
        "final_workspace_retained": bool(final_workspace),
        "auth_seed_mounted_read_only": True,
        "auth_seed_exported": False,
    })
    _write_manifest(trial_dir)
    print(
        f"[highlander] {trial_id}: {row['qualification']} outcome={row['outcome_score']}",
        flush=True,
    )
    return row


def _write_season_summary(
    run_dir: Path,
    protocol: dict[str, Any],
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    stage_id: str | None,
) -> dict[str, Any]:
    summary = aggregate_season(manifest, rows)
    summary.update({
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": _sha256((run_dir / "protocol.json").read_bytes()),
        "updated_at": _utc_now(),
        "last_stage": stage_id or "all",
        "claim_boundary": protocol["claim_boundary"],
        "process_score": None,
        "combined_score": None,
        "trial_rows": rows,
    })
    _write_json(run_dir / "summary.json", summary)
    (run_dir / "leaderboard.md").write_text(leaderboard_markdown(summary), encoding="utf-8")
    return summary


def _verify_inputs(protocol: dict[str, Any], upstream: Path, root: Path) -> None:
    if _git(upstream, "rev-parse", "HEAD") != protocol["upstream"]["commit"]:
        raise ValueError("upstream HarnessBench commit drifted")
    if _git(upstream, "rev-parse", "HEAD^{tree}") != protocol["upstream"]["tree"]:
        raise ValueError("upstream HarnessBench tree drifted")
    for relative, expected in protocol["source_hashes"].items():
        if _sha256((root / relative).read_bytes()) != expected:
            raise ValueError(f"Highlander season source drifted: {relative}")
    manifest_path = root / protocol["manifest"]["path"]
    if _sha256(manifest_path.read_bytes()) != protocol["manifest"]["sha256"]:
        raise ValueError("season manifest drifted")
    for task in protocol["tasks"]:
        task_dir = upstream / "tasks" / task["id"]
        observed = {
            path.relative_to(task_dir).as_posix(): _sha256(path.read_bytes())
            for path in _files_below(task_dir)
        }
        if observed != task["file_hashes"]:
            raise ValueError(f"HarnessBench task drifted: {task['id']}")


def _schedule(
    task_ids: Iterable[str], harness_ids: list[str], *, attempts: int, seed: int
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows = []
    sequence = 0
    for task_id in task_ids:
        for attempt in range(1, attempts + 1):
            block = list(harness_ids)
            rng.shuffle(block)
            for harness_id in block:
                sequence += 1
                rows.append({
                    "sequence": sequence,
                    "task_id": task_id,
                    "attempt": attempt,
                    "harness_id": harness_id,
                })
    return rows


def _stage_tasks(protocol: dict[str, Any], stage_id: str | None) -> set[str]:
    if stage_id is None:
        return {str(task["id"]) for task in protocol["tasks"]}
    for stage in protocol["execution_stages"]:
        if stage["id"] == stage_id:
            return {str(task_id) for task_id in stage["task_ids"]}
    raise ValueError(f"unknown execution stage: {stage_id}")


def _existing_results(run_dir: Path) -> list[dict[str, Any]]:
    ledger = run_dir / "results.jsonl"
    if not ledger.is_file():
        return []
    return [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]


def _ensure_frozen_copy(source: Path, destination: Path) -> None:
    raw = source.resolve().read_bytes()
    if destination.is_file():
        if destination.read_bytes() != raw:
            raise ValueError(f"frozen run input changed: {destination.name}")
        return
    destination.write_bytes(raw)


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_fixture_diff(base: Path, final: Path, output: Path) -> None:
    chunks: list[str] = []
    base_files = {path.relative_to(base) for path in base.rglob("*") if path.is_file()} if base.is_dir() else set()
    final_files = {path.relative_to(final) for path in final.rglob("*") if path.is_file()}
    for relative in sorted(base_files | final_files):
        left = (base / relative).read_bytes() if (base / relative).is_file() else b""
        right = (final / relative).read_bytes() if (final / relative).is_file() else b""
        if left == right:
            continue
        try:
            chunks.extend(difflib.unified_diff(
                left.decode("utf-8").splitlines(keepends=True),
                right.decode("utf-8").splitlines(keepends=True),
                fromfile=f"a/{relative.as_posix()}",
                tofile=f"b/{relative.as_posix()}",
            ))
        except UnicodeDecodeError:
            chunks.append(
                f"Binary files a/{relative.as_posix()} and b/{relative.as_posix()} differ "
                f"({_sha256(left)} -> {_sha256(right)})\n"
            )
    output.write_text("".join(chunks), encoding="utf-8")


def _write_manifest(root: Path) -> None:
    files = []
    for path in _files_below(root):
        if path.name == "artifact-manifest.json":
            continue
        raw = path.read_bytes()
        files.append({"path": path.relative_to(root).as_posix(), "bytes": len(raw), "sha256": _sha256(raw)})
    _write_json(root / "artifact-manifest.json", {"schema_version": 1, "generated_at": _utc_now(), "files": files})


def _files_below(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")

"""Disposable HarnessBench adapter for Highlander's pinned harness images."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .cleanroom import CleanRoom, extract_control_proof
from .hb_pilot import _process_metrics


SUPPORTED_HARNESSES = ("omp", "opencode", "codex", "hermes", "atomic", "nanobot")


def build_container_command(
    harness_id: str, lane: dict[str, Any], timeout_seconds: int
) -> list[str]:
    """Build the frozen clean-core invocation using in-container paths."""

    if harness_id not in SUPPORTED_HARNESSES:
        raise ValueError(f"unsupported clean HarnessBench harness: {harness_id}")
    model = str(lane["configured_model_id"])
    provider = str(lane["provider_id"])
    reasoning = str(lane["reasoning"])
    wire_reasoning = str(lane.get("wire_reasoning", reasoning))

    if harness_id == "omp":
        return [
            "omp",
            "--print",
            "--mode",
            "json",
            "--cwd",
            "/workspace",
            "--model",
            model,
            "--smol",
            model,
            "--slow",
            model,
            "--plan",
            model,
            "--thinking",
            reasoning,
            "--no-prewalk",
            "--no-title",
            "--no-session",
            "--no-extensions",
            "--no-skills",
            "--no-rules",
            "--approval-mode",
            "yolo",
            "--max-time",
            f"{timeout_seconds}s",
        ]
    if harness_id == "opencode":
        return [
            "opencode",
            "run",
            "--format",
            "json",
            "--dir",
            "/workspace",
            "--model",
            model,
            "--variant",
            wire_reasoning,
            "--auto",
            "--pure",
        ]
    if harness_id == "codex":
        return [
            "codex",
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--dangerously-bypass-approvals-and-sandbox",
            "--cd",
            "/workspace",
            "--model",
            model,
            "--config",
            f'model_reasoning_effort="{wire_reasoning}"',
            "--config",
            'cli_auth_credentials_store="file"',
        ]
    if harness_id == "hermes":
        return [
            "hermes",
            "--model",
            model,
            "--provider",
            provider,
            "--reasoning",
            wire_reasoning,
            "--yolo",
            "--safe-mode",
            "--usage-file",
            "/workspace/.highlander-usage.json",
            "--oneshot",
        ]
    if harness_id == "atomic":
        return [
            "atomic",
            "--mode",
            "json",
            "--print",
            "--provider",
            provider,
            "--model",
            model,
            "--thinking",
            reasoning,
            "--no-session",
            "--no-skills",
            "--no-prompt-templates",
            "--no-themes",
            "--no-context-files",
            "--no-approve",
            "--offline",
            "--",
        ]
    return [
        "env",
        f"NANOBOT_AGENTS__DEFAULTS__MODEL={model}",
        f"NANOBOT_AGENTS__DEFAULTS__PROVIDER={provider.replace('-', '_')}",
        f"NANOBOT_AGENTS__DEFAULTS__REASONING_EFFORT={wire_reasoning}",
        "NANOBOT_AGENTS__DEFAULTS__WORKSPACE=/workspace",
        "NANOBOT_TOOLS__RESTRICT_TO_WORKSPACE=true",
        "nanobot",
        "agent",
        "--workspace",
        "/workspace",
        "--session",
        "highlander:direct",
        "--no-markdown",
        "--logs",
        "--message",
    ]


def execute_clean_adapter(
    *,
    protocol: dict[str, Any],
    harness_id: str,
    workspace: Path,
    prompt_file: Path,
    evidence_dir: Path,
    trial_id: str,
) -> int:
    """Run one harness container and retain auth-free native evidence."""

    if harness_id not in SUPPORTED_HARNESSES:
        raise ValueError(f"unsupported clean HarnessBench harness: {harness_id}")
    workspace = workspace.resolve()
    prompt_file = prompt_file.resolve()
    evidence_dir = evidence_dir.resolve()
    if not workspace.is_dir() or not prompt_file.is_file():
        raise ValueError("HarnessBench workspace or prompt is unavailable")
    lanes = {str(item["id"]): item for item in protocol["harnesses"]}
    lane = lanes[harness_id]
    runtime = protocol["runtime"]
    limits = protocol["limits"]
    clean = CleanRoom(
        {
            "runtime": runtime["oci"],
            "profile": runtime["profile"],
            "network": runtime["network"],
            "cpus": runtime["cpus"],
            "memory_mb": runtime["memory_mb"],
            "pids_limit": runtime["pids_limit"],
            "tmpfs_mb": runtime["tmpfs_mb"],
            "evaluator_image": runtime["images"]["evaluator"],
        }
    )
    clean_plan = clean.plan_trial(
        match_id=trial_id,
        contender_id=harness_id,
        adapter=harness_id,
        image=runtime["images"][harness_id],
        seed_profile=str(lane["seed_profile"]),
        authentication_required=True,
    )
    if not clean_plan["seed"]["available"]:
        raise ValueError(f"authentication seed is unavailable for {harness_id}")
    command = build_container_command(
        harness_id, lane, int(limits["harness_wall_time_seconds"])
    )
    plan = {
        "adapter": harness_id,
        "worktree": str(workspace),
        "clean_room": clean_plan,
        "invocation": {
            "argv": command,
            "cwd": "/workspace",
            "prompt_transport": "exact rendered HarnessBench prompt appended as one argv element",
            "credential_values_recorded": False,
        },
    }
    evidence_dir.mkdir(parents=True, exist_ok=False)
    _write_json(evidence_dir / "container-plan.json", plan)
    _write_json(
        evidence_dir / "invocation.json",
        {
            "schema_version": 1,
            "harness_id": harness_id,
            "argv": [*command, "<TASK_BYTES_UTF8>"],
            "cwd": "/workspace",
            "prompt_sha256": _sha256(prompt_file.read_bytes()),
            "credential_binding": {
                "seed_profile": lane["seed_profile"],
                "value_retained": False,
            },
        },
    )
    output_path = evidence_dir / "stdout.raw"
    execution = clean.execute_harness(
        plan,
        prompt_file.read_text(encoding="utf-8"),
        output_path,
        int(limits["harness_wall_time_seconds"]),
    )
    (evidence_dir / "stderr.raw").write_text(
        "stderr was merged into stdout by the OCI controller\n", encoding="utf-8"
    )
    _write_json(evidence_dir / "execution.json", execution)
    usage_path = workspace / ".highlander-usage.json"
    if usage_path.is_file():
        shutil.move(str(usage_path), evidence_dir / "usage.json")
    metrics, ledger = _process_metrics(output_path.read_bytes())
    _write_json(evidence_dir / "process-metrics.json", metrics)
    with (evidence_dir / "tool-ledger.jsonl").open("w", encoding="utf-8") as handle:
        for row in ledger:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    expected = {
        "model": lane["expected_runtime_model_id"],
        "provider": lane["expected_runtime_provider_id"],
        "reasoning": lane["expected_runtime_reasoning"],
        "upstream_id": None,
        "endpoint_or_deployment": None,
        "region": None,
    }
    observed, _ = extract_control_proof(output_path, expected)
    proof = {
        "schema_version": 1,
        "configured_model_id": lane["configured_model_id"],
        "configured_provider_id": lane["provider_id"],
        "configured_reasoning": lane["reasoning"],
        "configured_verified": True,
        "fallback_policy": "forbidden",
        "observed": observed["observed"],
        "runtime_observation_available": any(
            observed["observed"].get(key) is not None
            for key in ("model", "provider", "reasoning")
        ),
        "runtime_verified": observed["runtime_verified"],
        "provider_wire_verified": observed["provider_verified"],
        "qualification_boundary": (
            "native runtime identity observed"
            if observed["runtime_verified"]
            else "configured route retained; exact wire identity not exposed by native output"
        ),
    }
    _write_json(evidence_dir / "control-proof.json", proof)
    return 124 if execution["timed_out"] else int(execution["returncode"])


def _sha256(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

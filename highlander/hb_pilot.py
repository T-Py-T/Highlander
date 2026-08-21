"""Controlled host-isolated HarnessBench pilot helpers.

The clean-room Match runner remains Highlander's preferred lane.  This module
exists for a separately labelled subscription-realism lane when disposable
credential seeds are unavailable.  It deliberately keeps outcome scoring,
process observations, and any combined score separate.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import random
import shutil
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping, Sequence


PROMPT_PLACEHOLDER = "__HIGHLANDER_PROMPT_BYTES_UTF8__"
SUPPORTED_HARNESSES = ("omp", "opencode", "codex", "hermes")


def build_host_invocation(
    harness_id: str,
    workspace: Path,
    prompt_file: Path,
    evidence_dir: Path,
    timeout_seconds: int,
) -> list[str]:
    """Return the frozen non-interactive argv with prompt bytes redacted.

    The wrapper replaces :data:`PROMPT_PLACEHOLDER` only in memory immediately
    before process creation.  Evidence therefore contains the exact control
    flags without duplicating potentially sensitive task bytes in argv logs.
    """

    if harness_id not in SUPPORTED_HARNESSES:
        raise ValueError(f"unsupported host pilot harness: {harness_id}")
    workspace = workspace.resolve()
    prompt_file = prompt_file.resolve()
    evidence_dir = evidence_dir.resolve()
    common_model = "gpt-5.4"

    if harness_id == "omp":
        qualified_model = f"openai-codex/{common_model}"
        return [
            "omp",
            "--print",
            "--mode",
            "json",
            "--cwd",
            str(workspace),
            "--model",
            qualified_model,
            "--smol",
            qualified_model,
            "--slow",
            qualified_model,
            "--plan",
            qualified_model,
            "--thinking",
            "medium",
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
            PROMPT_PLACEHOLDER,
        ]
    if harness_id == "opencode":
        return [
            "opencode",
            "run",
            "--format",
            "json",
            "--dir",
            str(workspace),
            "--model",
            f"openai/{common_model}",
            "--variant",
            "medium",
            "--auto",
            "--pure",
            PROMPT_PLACEHOLDER,
        ]
    if harness_id == "codex":
        return [
            "codex",
            "--ask-for-approval",
            "never",
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--cd",
            str(workspace),
            "--sandbox",
            "workspace-write",
            "--model",
            common_model,
            "--config",
            'model_reasoning_effort="medium"',
            "--config",
            'cli_auth_credentials_store="file"',
            PROMPT_PLACEHOLDER,
        ]
    return [
        "hermes",
        "--model",
        common_model,
        "--provider",
        "openai-codex",
        "--reasoning",
        "medium",
        "--yolo",
        "--safe-mode",
        "--usage-file",
        str(evidence_dir / "usage.json"),
        "--oneshot",
        PROMPT_PLACEHOLDER,
    ]


def build_host_environment(
    harness_id: str,
    profile_root: Path,
    evidence_dir: Path,
    *,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build a minimum environment without provider keys or daily config."""

    if harness_id not in SUPPORTED_HARNESSES:
        raise ValueError(f"unsupported host pilot harness: {harness_id}")
    source = dict(os.environ if base_env is None else base_env)
    preserve = {
        "PATH",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TERM",
        "TMPDIR",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "NODE_EXTRA_CA_CERTS",
    }
    env = {key: value for key, value in source.items() if key in preserve}
    env.update(
        {
            key: value
            for key, value in source.items()
            if key.startswith("HARNESSBENCH_")
        }
    )
    runtime_home = evidence_dir.resolve() / "runtime-home"
    env["HOME"] = str(runtime_home)
    env["NO_COLOR"] = "1"
    env["CI"] = "1"
    profile_root = profile_root.resolve()

    if harness_id == "omp":
        env["PI_CODING_AGENT_DIR"] = str(profile_root / "omp")
        env["PI_NO_PTY"] = "1"
    elif harness_id == "opencode":
        root = profile_root / "opencode"
        env["XDG_DATA_HOME"] = str(root / "data")
        env["XDG_CONFIG_HOME"] = str(root / "config")
        env["XDG_CACHE_HOME"] = str(runtime_home / "opencode-cache")
        env["XDG_STATE_HOME"] = str(runtime_home / "opencode-state")
    elif harness_id == "codex":
        env["CODEX_HOME"] = str(profile_root / "codex")
    else:
        env["HERMES_HOME"] = str(profile_root / "hermes")
    return env


def matched_block_schedule(
    harness_ids: Sequence[str], *, attempts: int, seed: int
) -> list[dict[str, int | str]]:
    """Return a deterministic randomized order with one lane per block."""

    if attempts < 1:
        raise ValueError("attempts must be positive")
    unknown = sorted(set(harness_ids) - set(SUPPORTED_HARNESSES))
    if unknown:
        raise ValueError(f"unsupported harnesses: {', '.join(unknown)}")
    if len(set(harness_ids)) != len(harness_ids):
        raise ValueError("harness_ids must be unique")
    rng = random.Random(seed)
    rows: list[dict[str, int | str]] = []
    sequence = 0
    for attempt in range(1, attempts + 1):
        block = list(harness_ids)
        rng.shuffle(block)
        for harness_id in block:
            sequence += 1
            rows.append(
                {
                    "sequence": sequence,
                    "attempt": attempt,
                    "harness_id": harness_id,
                }
            )
    return rows


def verify_frozen_protocol(protocol_path: Path, sidecar_path: Path) -> str:
    """Verify an immutable protocol sidecar and return its SHA-256."""

    import hashlib

    protocol_path = protocol_path.resolve()
    sidecar_path = sidecar_path.resolve()
    if not protocol_path.is_file() or not sidecar_path.is_file():
        raise ValueError("protocol or hash sidecar is unavailable")
    expected = sidecar_path.read_text(encoding="utf-8").strip().split()[0]
    observed = hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    if expected != observed:
        raise ValueError(
            f"protocol hash mismatch: expected {expected}, observed {observed}"
        )
    return observed


def aggregate_pilot(
    rows: Sequence[Mapping[str, object]], *, expected_attempts: int
) -> dict[str, object]:
    """Aggregate repeatability and process observations without ranking."""

    harness_ids = sorted({str(row["harness_id"]) for row in rows})
    harnesses: list[dict[str, object]] = []
    for harness_id in harness_ids:
        lane = [row for row in rows if str(row["harness_id"]) == harness_id]
        valid = [row for row in lane if row.get("qualification") == "valid"]
        scores = [float(row["outcome_score"]) for row in valid]
        elapsed = [
            float(row["elapsed_seconds"])
            for row in valid
            if isinstance(row.get("elapsed_seconds"), (int, float))
        ]
        tool_events = [
            int(row["tool_event_count"])
            for row in valid
            if isinstance(row.get("tool_event_count"), int)
        ]
        harnesses.append(
            {
                "harness_id": harness_id,
                "expected_trials": expected_attempts,
                "valid_trials": len(valid),
                "invalid_trials": sum(row.get("qualification") == "invalid" for row in lane),
                "unavailable_trials": sum(
                    row.get("qualification") == "unavailable" for row in lane
                ),
                "mean_outcome": round(statistics.fmean(scores), 4) if scores else None,
                "population_stddev": round(statistics.pstdev(scores), 4)
                if scores
                else None,
                "sample_stddev": round(statistics.stdev(scores), 4)
                if len(scores) > 1
                else None,
                "minimum_outcome": min(scores) if scores else None,
                "maximum_outcome": max(scores) if scores else None,
                "mean_elapsed_seconds": round(statistics.fmean(elapsed), 3)
                if elapsed
                else None,
                "total_tool_events": sum(tool_events) if tool_events else None,
                "operator_interventions": sum(
                    int(row.get("operator_interventions", 0) or 0) for row in lane
                ),
            }
        )
    return {
        "claim_status": "underpowered_single_task_pilot",
        "winner": None,
        "ranking_permitted": False,
        "process_score": None,
        "combined_score": None,
        "harnesses": harnesses,
    }


def classify_harnessbench_result(
    payload: Mapping[str, object], *, wrapper_execution: Mapping[str, object]
) -> dict[str, object]:
    """Qualify a result and retain only the deterministic outcome score.

    HarnessBench assigns a default process grade when its LLM judge is skipped;
    that value and its derived combined score are not measurements.  Highlander
    records both as ``None`` for this pilot.
    """

    adapter = payload.get("adapter_result")
    adapter_ok = isinstance(adapter, Mapping) and adapter.get("ok") is True
    timed_out = wrapper_execution.get("timed_out") is True
    wrapper_ok = wrapper_execution.get("returncode") == 0 and not timed_out
    oracle = payload.get("oracle_result")
    if not adapter_ok or not wrapper_ok or not isinstance(oracle, Mapping):
        if timed_out:
            reason = "harness_timeout"
        elif not wrapper_ok:
            reason = "harness_nonzero_exit"
        elif not adapter_ok:
            reason = "upstream_adapter_failure"
        else:
            reason = "oracle_result_missing"
        return {
            "qualification": "invalid",
            "invalid_reason": reason,
            "outcome_score": None,
            "process_status": "not_evaluated",
            "process_score": None,
            "combined_score": None,
        }
    score = oracle.get("outcome_score", oracle.get("score"))
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return {
            "qualification": "invalid",
            "invalid_reason": "deterministic_outcome_score_missing",
            "outcome_score": None,
            "process_status": "not_evaluated",
            "process_score": None,
            "combined_score": None,
        }
    return {
        "qualification": "valid",
        "invalid_reason": None,
        "outcome_score": float(score),
        "process_status": "not_evaluated",
        "process_score": None,
        "combined_score": None,
    }


def execute_host_harness(
    harness_id: str,
    *,
    workspace: Path,
    prompt_file: Path,
    evidence_dir: Path,
    profile_root: Path,
    timeout_seconds: int,
) -> int:
    """Execute one host-isolated contender and retain bounded native evidence."""

    workspace = workspace.resolve()
    prompt_file = prompt_file.resolve()
    evidence_dir = evidence_dir.resolve()
    profile_root = profile_root.resolve()
    if not workspace.is_dir():
        raise ValueError(f"workspace is unavailable: {workspace}")
    if not prompt_file.is_file():
        raise ValueError(f"prompt file is unavailable: {prompt_file}")
    profile_dir = profile_root / harness_id
    if not profile_dir.is_dir():
        raise ValueError(f"dedicated profile is unavailable for {harness_id}")

    evidence_dir.mkdir(parents=True, exist_ok=True)
    prompt = prompt_file.read_text(encoding="utf-8")
    redacted_argv = build_host_invocation(
        harness_id, workspace, prompt_file, evidence_dir, timeout_seconds
    )
    actual_argv = [prompt if value == PROMPT_PLACEHOLDER else value for value in redacted_argv]
    evidence_argv = [
        "<TASK_BYTES_UTF8>" if value == PROMPT_PLACEHOLDER else value
        for value in redacted_argv
    ]
    env = build_host_environment(harness_id, profile_root, evidence_dir)
    Path(env["HOME"]).mkdir(parents=True, exist_ok=True)
    for key in ("XDG_CACHE_HOME", "XDG_STATE_HOME"):
        if key in env:
            Path(env[key]).mkdir(parents=True, exist_ok=True)

    profile_env = {
        "omp": "PI_CODING_AGENT_DIR",
        "opencode": "XDG_DATA_HOME",
        "codex": "CODEX_HOME",
        "hermes": "HERMES_HOME",
    }[harness_id]
    invocation = {
        "schema_version": 1,
        "harness_id": harness_id,
        "argv": evidence_argv,
        "cwd": str(workspace),
        "prompt_source": "HarnessBench rendered prompt file",
        "prompt_bytes": len(prompt.encode("utf-8")),
        "environment_names": sorted(env),
        "credential_binding": {
            "profile_id": f"hb-gpt54-20260808/{harness_id}",
            "environment_name": profile_env,
            "value_retained": False,
        },
    }
    _write_json(evidence_dir / "invocation.json", invocation)

    started_ns = time.time_ns()
    started_at = _utc_now()
    process = subprocess.Popen(
        actual_argv,
        cwd=workspace,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()

    returncode = 124 if timed_out else int(process.returncode)
    (evidence_dir / "stdout.raw").write_bytes(stdout)
    (evidence_dir / "stderr.raw").write_bytes(stderr)
    metrics, ledger = _process_metrics(stdout)
    with (evidence_dir / "tool-ledger.jsonl").open("w", encoding="utf-8") as handle:
        for row in ledger:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    runtime_home = Path(env["HOME"])
    shutil.rmtree(runtime_home, ignore_errors=True)
    execution = {
        "schema_version": 1,
        "harness_id": harness_id,
        "started_at": started_at,
        "completed_at": _utc_now(),
        "started_ns": started_ns,
        "completed_ns": time.time_ns(),
        "elapsed_seconds": round((time.time_ns() - started_ns) / 1_000_000_000, 3),
        "returncode": returncode,
        "timed_out": timed_out,
        "process_metrics": metrics,
        "temporary_home_removed": not runtime_home.exists(),
        "operator_interventions": 0,
    }
    _write_json(evidence_dir / "execution.json", execution)
    if stdout:
        sys.stdout.buffer.write(stdout)
        sys.stdout.buffer.flush()
    if stderr:
        sys.stderr.buffer.write(stderr)
        sys.stderr.buffer.flush()
    return returncode


def _process_metrics(stdout: bytes) -> tuple[dict[str, int], list[dict[str, object]]]:
    events = 0
    tool_events = 0
    ledger: list[dict[str, object]] = []
    for line_number, line in enumerate(stdout.decode("utf-8", errors="replace").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        events += 1
        event_type = str(row.get("type", "")).lower()
        tool_name = row.get("tool_name") or row.get("tool") or row.get("name")
        is_tool = "tool" in event_type or "command" in event_type or tool_name is not None
        if is_tool:
            tool_events += 1
            ledger.append(
                {
                    "line": line_number,
                    "type": row.get("type"),
                    "tool_name": tool_name,
                    "status": row.get("status"),
                }
            )
    return {"event_count": events, "tool_event_count": tool_events}, ledger


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")

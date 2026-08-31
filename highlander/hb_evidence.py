"""Sanitize, normalize, and verify retained HarnessBench pilot evidence."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
from pathlib import Path
from typing import Any, Iterable

from .season import aggregate_season, leaderboard_markdown


class PilotEvidenceError(RuntimeError):
    """Pilot evidence cannot be exported without weakening its claims."""


_SECRET_PATTERNS = {
    "private_key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "github_token": re.compile(rb"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}"),
    "openai_key": re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    "bearer_token": re.compile(rb"Bearer\s+[A-Za-z0-9._~+/-]{20,}", re.I),
    "oauth_token": re.compile(
        rb'"(?:access_token|refresh_token|id_token)"\s*:\s*"[^"\\]{8,}"',
        re.I,
    ),
}
_PROVIDER_ENCRYPTED_FIELD = re.compile(
    r'(?P<prefix>\\*"(?:encrypted_content|encryptedContent)\\*"\s*:\s*\\*")'
    r'(?P<value>[^"\\]+)(?P<suffix>\\*")'
)
_PROVIDER_ENCRYPTED_REDACTION = "<PROVIDER_ENCRYPTED_PAYLOAD_REDACTED>"


def export_pilot_bundle(
    source: str | Path,
    destination: str | Path,
    runner_repository: str | Path,
) -> dict[str, Any]:
    """Create a path-safe public copy while retaining native transcripts."""

    source_supplied = Path(source).expanduser().absolute()
    source_root = source_supplied.resolve()
    destination_root = Path(destination).expanduser().resolve()
    runner_supplied = Path(runner_repository).expanduser().absolute()
    runner_root = runner_supplied.resolve()
    if not source_root.is_dir():
        raise PilotEvidenceError(f"source pilot does not exist: {source_root}")
    if destination_root.exists():
        raise PilotEvidenceError(
            f"destination already exists; pilot exports are immutable: {destination_root}"
        )
    if destination_root == source_root or source_root in destination_root.parents:
        raise PilotEvidenceError("destination cannot be inside the private source")

    source_manifest_path = source_root / "artifact-manifest.json"
    source_manifest = _load_json(source_manifest_path, "source manifest")
    source_artifacts = _verify_private_manifest(source_root, source_manifest)
    protocol = _load_json(source_root / "protocol.json", "pilot protocol")
    first_summary = _load_json(source_root / "summary.json", "first-pass summary")
    runner = _runner_provenance(runner_root)
    replacements = _redaction_roots(
        source_supplied,
        source_root,
        runner_supplied,
        runner_root,
    )
    temporary = destination_root.with_name(destination_root.name + ".exporting")
    if temporary.exists():
        raise PilotEvidenceError(f"stale temporary export exists: {temporary}")
    temporary.mkdir(parents=True)
    counts = {placeholder: 0 for _, placeholder in replacements}
    counts[_PROVIDER_ENCRYPTED_REDACTION] = 0
    try:
        for relative in source_artifacts:
            source_path = source_root / relative
            destination_path = temporary / relative
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            sanitized, observed = _sanitize_bytes(source_path.read_bytes(), replacements)
            _reject_secret_material(relative, sanitized)
            destination_path.write_bytes(sanitized)
            for placeholder, count in observed.items():
                counts[placeholder] += count

        shutil.copy2(temporary / "summary.json", temporary / "summary.runner-first-pass.json")
        if (temporary / "report.md").is_file():
            shutil.copy2(temporary / "report.md", temporary / "report.runner-first-pass.md")

        rows: list[dict[str, Any]] = []
        for result_path in sorted((temporary / "trials").glob("*/result.json")):
            row = _load_json(result_path, "trial result")
            native_dir = result_path.parent / "native"
            process, ledger = _normalize_process(row["harness_id"], native_dir)
            usage = _normalize_usage(row["harness_id"], native_dir)
            row.pop("tool_event_count", None)
            row.pop("event_count", None)
            row.pop("usage", None)
            row["process_observations"] = process
            row["usage_normalized"] = usage
            _write_json(result_path, row)
            process_dir = result_path.parent / "process"
            process_dir.mkdir(exist_ok=True)
            _write_json(process_dir / "observations.json", process)
            with (process_dir / "tool-invocations.jsonl").open(
                "w", encoding="utf-8"
            ) as handle:
                for event in ledger:
                    handle.write(json.dumps(event, sort_keys=True) + "\n")
            _write_json(result_path.parent / "usage-normalized.json", usage)
            _write_public_manifest(result_path.parent)
            rows.append(row)

        represented = {str(row["harness_id"]) for row in rows}
        for row in first_summary.get("trial_rows", []):
            if (
                isinstance(row, dict)
                and row.get("qualification") == "unavailable"
                and str(row.get("harness_id")) not in represented
            ):
                rows.append(dict(row))
        summary = _aggregate(protocol, rows)
        summary.update(
            {
                "schema_version": 1,
                "protocol_id": protocol["protocol_id"],
                "protocol_sha256": first_summary.get("protocol_sha256"),
                "task_id": protocol["task"]["id"],
                "completed_at": first_summary.get("completed_at"),
                "exported_at": _utc_now(),
                "claim_boundary": protocol["claim_boundary"],
                "trial_rows": rows,
            }
        )
        _write_json(temporary / "summary.json", summary)
        with (temporary / "results.jsonl").open("w", encoding="utf-8") as handle:
            for row in sorted(summary["trial_rows"], key=lambda item: int(item["sequence"])):
                handle.write(
                    json.dumps(
                        {
                            "run_id": (
                                f"{protocol['protocol_id']}-{row['harness_id']}-"
                                f"{int(row['attempt']):03d}"
                            ),
                            "protocol_id": protocol["protocol_id"],
                            "task_id": row["task_id"],
                            "harness_id": row["harness_id"],
                            "attempt": row["attempt"],
                            "sequence": row["sequence"],
                            "qualification": row["qualification"],
                            "invalid_reason": row.get("invalid_reason"),
                            "outcome_score": row.get("outcome_score"),
                            "process_score": None,
                            "combined_score": None,
                            "elapsed_seconds": (
                                row.get("process_observations", {}).get(
                                    "elapsed_seconds"
                                )
                                if isinstance(row.get("process_observations"), dict)
                                else None
                            ),
                            "intervention_count": row.get(
                                "operator_interventions", 0
                            ),
                            "artifacts": row.get("artifacts"),
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
        _write_json(
            temporary / "leaderboard.json",
            {
                "schema_version": 1,
                "protocol_id": protocol["protocol_id"],
                "task_id": protocol["task"]["id"],
                "claim_status": summary["claim_status"],
                "ranking_permitted": False,
                "winner": None,
                "process_score": None,
                "combined_score": None,
                "harnesses": summary["harnesses"],
            },
        )
        (temporary / "report.md").write_text(
            _report(protocol, summary), encoding="utf-8"
        )
        _write_json(
            temporary / "runner-provenance.json",
            {
                "schema_version": 1,
                "runner": runner,
                "protocol_id": protocol["protocol_id"],
                "protocol_sha256": first_summary.get("protocol_sha256"),
                "source_artifact_manifest_sha256": _sha256(
                    source_manifest_path.read_bytes()
                ),
                "normalization": {
                    "process_score": None,
                    "combined_score": None,
                    "tool_counts": "native invocation starts only",
                    "usage": "native harness reports; accounting is not cross-harness comparable",
                },
            },
        )
        _write_json(
            temporary / "redaction-report.json",
            {
                "schema_version": 1,
                "method": "exact-root replacement plus high-confidence secret scan",
                "replacements": [
                    {"placeholder": placeholder, "occurrences": counts[placeholder]}
                    for _, placeholder in replacements
                ],
                "secret_patterns_checked": sorted(_SECRET_PATTERNS),
                "native_transcripts_exported": True,
                "provider_encrypted_payloads_redacted": counts[
                    _PROVIDER_ENCRYPTED_REDACTION
                ],
                "credential_values_exported": False,
                "private_raw_source_retained": True,
            },
        )

        for path in _files_below(temporary):
            raw = path.read_bytes()
            _reject_secret_material(path.relative_to(temporary), raw)
            for root_value, _ in replacements:
                if root_value.encode("utf-8") in raw:
                    raise PilotEvidenceError(
                        f"redaction root remains in {path.relative_to(temporary)}"
                    )
        _write_public_manifest(temporary)
        destination_root.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary, destination_root)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return verify_pilot_bundle(destination_root)


def verify_pilot_bundle(bundle: str | Path) -> dict[str, Any]:
    """Verify exact public membership, hashes, nested manifests, and claims."""

    root = Path(bundle).expanduser().resolve()
    manifest = _load_json(root / "artifact-manifest.json", "public manifest")
    artifacts = _verify_public_manifest(root, manifest)
    actual = {
        path.relative_to(root).as_posix()
        for path in _files_below(root)
        if path.name != "artifact-manifest.json"
    }
    expected = {path.as_posix() for path in artifacts}
    if actual != expected:
        raise PilotEvidenceError(
            f"public membership mismatch: extra={sorted(actual - expected)}, "
            f"missing={sorted(expected - actual)}"
        )
    for nested in (root / "trials").glob("*/artifact-manifest.json"):
        _verify_public_manifest(nested.parent, _load_json(nested, "trial manifest"))
    summary = _load_json(root / "summary.json", "pilot summary")
    if summary.get("winner") is not None or summary.get("ranking_permitted") is not False:
        raise PilotEvidenceError("underpowered pilot cannot contain a winner or ranking")
    if summary.get("process_score") is not None or summary.get("combined_score") is not None:
        raise PilotEvidenceError("unevaluated process/combined scores must remain null")
    return {
        "status": "verified",
        "bundle": str(root),
        "artifact_count": len(artifacts),
        "manifest_sha256": _sha256((root / "artifact-manifest.json").read_bytes()),
    }


def export_season_bundle(
    source: str | Path,
    destination: str | Path,
    runner_repository: str | Path,
) -> dict[str, Any]:
    """Create an immutable, path-redacted public copy of a scored season."""

    source_supplied = Path(source).expanduser().absolute()
    source_root = source_supplied.resolve()
    destination_root = Path(destination).expanduser().resolve()
    runner_supplied = Path(runner_repository).expanduser().absolute()
    runner_root = runner_supplied.resolve()
    if not source_root.is_dir():
        raise PilotEvidenceError(f"source season does not exist: {source_root}")
    if destination_root.exists():
        raise PilotEvidenceError(
            f"destination already exists; season exports are immutable: {destination_root}"
        )
    if destination_root == source_root or source_root in destination_root.parents:
        raise PilotEvidenceError("destination cannot be inside the private source")

    source_manifest_path = source_root / "artifact-manifest.json"
    source_artifacts = _verify_private_manifest(
        source_root, _load_json(source_manifest_path, "source manifest")
    )
    protocol = _load_json(source_root / "protocol.json", "season protocol")
    manifest = _load_json(source_root / "season-manifest.json", "season manifest")
    first_summary = _load_json(source_root / "summary.json", "first-pass summary")
    runner = _runner_provenance(runner_root)
    replacements = _redaction_roots(
        source_supplied, source_root, runner_supplied, runner_root
    )
    temporary = destination_root.with_name(destination_root.name + ".exporting")
    if temporary.exists():
        raise PilotEvidenceError(f"stale temporary export exists: {temporary}")
    temporary.mkdir(parents=True)
    counts = {placeholder: 0 for _, placeholder in replacements}
    counts[_PROVIDER_ENCRYPTED_REDACTION] = 0
    try:
        for relative in source_artifacts:
            source_path = source_root / relative
            destination_path = temporary / relative
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            sanitized, observed = _sanitize_bytes(source_path.read_bytes(), replacements)
            _reject_secret_material(relative, sanitized)
            destination_path.write_bytes(sanitized)
            for placeholder, count in observed.items():
                counts[placeholder] += count

        shutil.copy2(temporary / "summary.json", temporary / "summary.runner-first-pass.json")
        if (temporary / "leaderboard.md").is_file():
            shutil.copy2(
                temporary / "leaderboard.md",
                temporary / "leaderboard.runner-first-pass.md",
            )
        rows: list[dict[str, Any]] = []
        for result_path in sorted((temporary / "trials").glob("*/result.json")):
            row = _load_json(result_path, "season trial result")
            native_dir = result_path.parent / "native"
            if (
                (native_dir / "stdout.raw").is_file()
                and (native_dir / "execution.json").is_file()
            ):
                process, ledger = _normalize_process(row["harness_id"], native_dir)
                usage = _normalize_usage(row["harness_id"], native_dir)
            else:
                process = {
                    "status": "unavailable",
                    "native_observability": "no_native_execution",
                    "native_event_count": None,
                    "tool_invocation_count": None,
                    "elapsed_seconds": row.get("elapsed_seconds"),
                    "operator_interventions": row.get("intervention_count", 0),
                    "process_score": None,
                    "combined_score": None,
                    "cross_harness_comparability": "not available",
                }
                usage = {
                    "available": False,
                    "source": None,
                    "cross_harness_comparability": "not available",
                }
                ledger = []
            row["process_observations"] = process
            row["usage_normalized"] = usage
            row["process_score"] = None
            row["combined_score"] = None
            _write_json(result_path, row)
            process_dir = result_path.parent / "process"
            process_dir.mkdir(exist_ok=True)
            _write_json(process_dir / "observations.json", process)
            with (process_dir / "tool-invocations.jsonl").open(
                "w", encoding="utf-8"
            ) as handle:
                for event in ledger:
                    handle.write(json.dumps(event, sort_keys=True) + "\n")
            _write_json(result_path.parent / "usage-normalized.json", usage)
            _write_public_manifest(result_path.parent)
            rows.append(row)

        summary = aggregate_season(manifest, rows)
        summary.update(
            {
                "protocol_id": protocol["protocol_id"],
                "protocol_sha256": first_summary.get("protocol_sha256"),
                "completed_at": first_summary.get("updated_at"),
                "exported_at": _utc_now(),
                "claim_boundary": protocol["claim_boundary"],
                "process_score": None,
                "combined_score": None,
                "trial_rows": rows,
            }
        )
        _write_json(temporary / "summary.json", summary)
        with (temporary / "results.jsonl").open("w", encoding="utf-8") as handle:
            for row in sorted(rows, key=lambda item: (int(item["sequence"]), int(item.get("retry", 1)))):
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        leaderboard = {key: value for key, value in summary.items() if key != "trial_rows"}
        _write_json(temporary / "leaderboard.json", leaderboard)
        (temporary / "leaderboard.md").write_text(
            leaderboard_markdown(summary), encoding="utf-8"
        )
        _write_json(
            temporary / "runner-provenance.json",
            {
                "schema_version": 1,
                "runner": runner,
                "protocol_id": protocol["protocol_id"],
                "protocol_sha256": first_summary.get("protocol_sha256"),
                "source_artifact_manifest_sha256": _sha256(
                    source_manifest_path.read_bytes()
                ),
                "normalization": {
                    "process_score": None,
                    "combined_score": None,
                    "tool_counts": "native invocation starts where observable",
                    "usage": "native reports; accounting is not cross-harness comparable",
                },
            },
        )
        _write_json(
            temporary / "redaction-report.json",
            {
                "schema_version": 1,
                "method": "exact-root replacement plus high-confidence secret scan",
                "replacements": [
                    {"placeholder": placeholder, "occurrences": counts[placeholder]}
                    for _, placeholder in replacements
                ],
                "secret_patterns_checked": sorted(_SECRET_PATTERNS),
                "native_transcripts_exported": True,
                "provider_encrypted_payloads_redacted": counts[
                    _PROVIDER_ENCRYPTED_REDACTION
                ],
                "credential_values_exported": False,
                "private_raw_source_retained": True,
            },
        )
        for path in _files_below(temporary):
            raw = path.read_bytes()
            _reject_secret_material(path.relative_to(temporary), raw)
            for root_value, _ in replacements:
                if root_value.encode("utf-8") in raw:
                    raise PilotEvidenceError(
                        f"redaction root remains in {path.relative_to(temporary)}"
                    )
        _write_public_manifest(temporary)
        destination_root.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary, destination_root)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return verify_season_bundle(destination_root)


def verify_season_bundle(bundle: str | Path) -> dict[str, Any]:
    """Verify membership, hashes, deterministic aggregation, and score boundaries."""

    root = Path(bundle).expanduser().resolve()
    artifacts = _verify_public_manifest(
        root, _load_json(root / "artifact-manifest.json", "public manifest")
    )
    actual = {
        path.relative_to(root).as_posix()
        for path in _files_below(root)
        if path.name != "artifact-manifest.json"
    }
    expected = {path.as_posix() for path in artifacts}
    if actual != expected:
        raise PilotEvidenceError(
            f"public membership mismatch: extra={sorted(actual - expected)}, "
            f"missing={sorted(expected - actual)}"
        )
    for nested in (root / "trials").glob("*/artifact-manifest.json"):
        _verify_public_manifest(nested.parent, _load_json(nested, "trial manifest"))
    manifest = _load_json(root / "season-manifest.json", "season manifest")
    rows = [
        json.loads(line)
        for line in (root / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        if row.get("process_score") is not None or row.get("combined_score") is not None:
            raise PilotEvidenceError("unevaluated process and combined scores must be null")
    observed = aggregate_season(manifest, rows)
    published = _load_json(root / "leaderboard.json", "season leaderboard")
    for key in ("season_id", "pack_id", "status", "ranking_contract", "contenders"):
        if published.get(key) != observed.get(key):
            raise PilotEvidenceError(f"published leaderboard drifted at {key}")
    return {
        "status": "verified",
        "bundle": str(root),
        "artifact_count": len(artifacts),
        "manifest_sha256": _sha256((root / "artifact-manifest.json").read_bytes()),
        "season_status": observed["status"],
    }


def _normalize_process(
    harness_id: str, native_dir: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    stdout = (native_dir / "stdout.raw").read_text(
        encoding="utf-8", errors="replace"
    )
    execution = _load_json(native_dir / "execution.json", "native execution")
    event_count = 0
    ledger: list[dict[str, Any]] = []
    for line_number, line in enumerate(stdout.splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        event_count += 1
        event = _tool_invocation(harness_id, row, line_number)
        if event:
            ledger.append(event)
    observable = harness_id != "hermes"
    return (
        {
            "status": "observed_not_scored",
            "native_observability": "event_stream" if observable else "final_response_only",
            "native_event_count": event_count if observable else None,
            "tool_invocation_count": len(ledger) if observable else None,
            "elapsed_seconds": execution.get("elapsed_seconds"),
            "operator_interventions": execution.get("operator_interventions", 0),
            "process_score": None,
            "combined_score": None,
            "cross_harness_comparability": "limited by native event semantics",
        },
        ledger,
    )


def _tool_invocation(
    harness_id: str, row: dict[str, Any], line_number: int
) -> dict[str, Any] | None:
    event_type = str(row.get("type", ""))
    tool_kind: Any = None
    if harness_id in {"omp", "atomic"} and event_type == "tool_execution_start":
        tool_kind = row.get("toolName") or row.get("tool_name") or "tool"
    elif harness_id == "opencode" and event_type == "tool_use":
        part = row.get("part")
        tool_kind = (
            part.get("tool") or part.get("toolName") or part.get("type")
            if isinstance(part, dict)
            else row.get("tool") or "tool"
        )
    elif harness_id == "codex" and event_type == "item.started":
        item = row.get("item")
        if isinstance(item, dict) and item.get("type") in {
            "command_execution",
            "file_change",
            "mcp_tool_call",
            "dynamic_tool_call",
            "web_search",
            "computer_action",
        }:
            tool_kind = item.get("type")
    if tool_kind is None:
        return None
    return {"line": line_number, "event_type": event_type, "tool_kind": tool_kind}


def _normalize_usage(harness_id: str, native_dir: Path) -> dict[str, Any]:
    records = _json_lines(native_dir / "stdout.raw")
    base: dict[str, Any] = {
        "available": False,
        "source": None,
        "api_calls": None,
        "input_tokens": None,
        "output_tokens": None,
        "cache_read_tokens": None,
        "cache_write_tokens": None,
        "reasoning_tokens": None,
        "total_tokens": None,
        "models": [],
        "providers": [],
        "cost_usd": None,
        "cost_status": "not_available",
        "cross_harness_comparability": "not comparable; native accounting semantics differ",
    }
    if harness_id == "hermes":
        usage_path = native_dir / "usage.json"
        if not usage_path.is_file():
            return base
        row = _load_json(usage_path, "Hermes usage")
        return {
            **base,
            "available": True,
            "source": "hermes_native_usage_file",
            "api_calls": row.get("api_calls"),
            "input_tokens": row.get("input_tokens"),
            "output_tokens": row.get("output_tokens"),
            "cache_read_tokens": row.get("cache_read_tokens"),
            "cache_write_tokens": row.get("cache_write_tokens"),
            "reasoning_tokens": row.get("reasoning_tokens"),
            "total_tokens": row.get("total_tokens"),
            "models": [row["model"]] if row.get("model") else [],
            "providers": [row["provider"]] if row.get("provider") else [],
            "cost_usd": row.get("estimated_cost_usd"),
            "cost_status": "native_report_says_no_cost_source",
        }
    if harness_id == "codex":
        usages = [row.get("usage") for row in records if row.get("type") == "turn.completed"]
        usage = next((row for row in reversed(usages) if isinstance(row, dict)), None)
        if not usage:
            return base
        return {
            **base,
            "available": True,
            "source": "codex_turn_completed",
            "api_calls": None,
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "cache_read_tokens": usage.get("cached_input_tokens"),
            "cache_write_tokens": usage.get("cache_write_input_tokens"),
            "reasoning_tokens": usage.get("reasoning_output_tokens"),
            "total_tokens": _sum_optional(
                usage.get("input_tokens"), usage.get("output_tokens")
            ),
        }
    if harness_id == "opencode":
        token_rows = []
        costs = []
        for row in records:
            if row.get("type") != "step_finish" or not isinstance(row.get("part"), dict):
                continue
            part = row["part"]
            if isinstance(part.get("tokens"), dict):
                token_rows.append(part["tokens"])
            if isinstance(part.get("cost"), (int, float)):
                costs.append(float(part["cost"]))
        if not token_rows:
            return base
        return {
            **base,
            "available": True,
            "source": "opencode_step_finish",
            "api_calls": len(token_rows),
            "input_tokens": sum(int(row.get("input", 0) or 0) for row in token_rows),
            "output_tokens": sum(int(row.get("output", 0) or 0) for row in token_rows),
            "cache_read_tokens": sum(
                int((row.get("cache") or {}).get("read", 0) or 0)
                for row in token_rows
            ),
            "cache_write_tokens": sum(
                int((row.get("cache") or {}).get("write", 0) or 0)
                for row in token_rows
            ),
            "reasoning_tokens": sum(
                int(row.get("reasoning", 0) or 0) for row in token_rows
            ),
            "total_tokens": sum(int(row.get("total", 0) or 0) for row in token_rows),
            "cost_usd": round(sum(costs), 8) if costs else None,
            "cost_status": "native_value_not_subscription_comparable",
        }
    if harness_id not in {"omp", "atomic"}:
        return base
    usage_rows = []
    models: set[str] = set()
    providers: set[str] = set()
    for row in records:
        if row.get("type") != "message_end" or not isinstance(row.get("message"), dict):
            continue
        message = row["message"]
        usage = message.get("usage")
        if message.get("role") == "assistant" and isinstance(usage, dict):
            usage_rows.append(usage)
            if message.get("model"):
                models.add(str(message["model"]))
            if message.get("provider"):
                providers.add(str(message["provider"]))
    if not usage_rows:
        return base
    costs = [
        float((row.get("cost") or {}).get("total", 0) or 0) for row in usage_rows
    ]
    return {
        **base,
        "available": True,
        "source": "omp_assistant_message_end",
        "api_calls": len(usage_rows),
        "input_tokens": sum(int(row.get("input", 0) or 0) for row in usage_rows),
        "output_tokens": sum(int(row.get("output", 0) or 0) for row in usage_rows),
        "cache_read_tokens": sum(int(row.get("cacheRead", 0) or 0) for row in usage_rows),
        "cache_write_tokens": sum(int(row.get("cacheWrite", 0) or 0) for row in usage_rows),
        "reasoning_tokens": sum(int(row.get("reasoningTokens", 0) or 0) for row in usage_rows),
        "total_tokens": sum(int(row.get("totalTokens", 0) or 0) for row in usage_rows),
        "models": sorted(models),
        "providers": sorted(providers),
        "cost_usd": round(sum(costs), 8),
        "cost_status": "harness_estimate_not_subscription_comparable",
    }


def _aggregate(protocol: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected = int(protocol["attempts_per_harness_task"])
    harness_ids = {str(row["id"]) for row in protocol.get("harnesses", [])}
    harness_ids.update(str(row["harness_id"]) for row in rows)
    output = []
    for harness_id in sorted(harness_ids):
        lane = [row for row in rows if str(row["harness_id"]) == harness_id]
        valid = [row for row in lane if row.get("qualification") == "valid"]
        scores = [float(row["outcome_score"]) for row in valid]
        processes = [row.get("process_observations") for row in valid]
        processes = [row for row in processes if isinstance(row, dict)]
        elapsed = [
            float(row["elapsed_seconds"])
            for row in processes
            if isinstance(row.get("elapsed_seconds"), (int, float))
        ]
        tool_counts = [
            int(row["tool_invocation_count"])
            for row in processes
            if isinstance(row.get("tool_invocation_count"), int)
        ]
        output.append(
            {
                "harness_id": harness_id,
                "expected_trials": expected,
                "valid_trials": len(valid),
                "invalid_trials": sum(row.get("qualification") == "invalid" for row in lane),
                "unavailable_trials": sum(
                    row.get("qualification") == "unavailable" for row in lane
                ),
                "mean_outcome": round(statistics.fmean(scores), 4) if scores else None,
                "population_stddev": round(statistics.pstdev(scores), 4) if scores else None,
                "sample_stddev": round(statistics.stdev(scores), 4)
                if len(scores) > 1
                else None,
                "minimum_outcome": min(scores) if scores else None,
                "maximum_outcome": max(scores) if scores else None,
                "mean_elapsed_seconds": round(statistics.fmean(elapsed), 3)
                if elapsed
                else None,
                "tool_invocations_observed_total": sum(tool_counts)
                if tool_counts
                else None,
                "tool_observation_coverage": f"{len(tool_counts)}/{len(valid)}",
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
        "harnesses": output,
    }


def _report(protocol: dict[str, Any], summary: dict[str, Any]) -> str:
    lines = [
        f"# {protocol['protocol_id']}",
        "",
        f"Protocol SHA-256: `{summary.get('protocol_sha256')}`",
        "",
        "> Claim boundary: one deterministic hard task with three repeats per available "
        "host-isolated harness. This pilot does not declare a winner or generalize across tasks.",
        "",
        "Process and combined scores were not evaluated. Native process and usage facts are retained separately and are not assumed cross-harness comparable.",
        "",
        "| Harness | Trials | Scores | Mean | Population σ | Mean seconds | Observed tool invocations |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    trial_rows = summary["trial_rows"]
    for harness in summary["harnesses"]:
        scores = [
            row.get("outcome_score")
            for row in trial_rows
            if row.get("harness_id") == harness["harness_id"]
            and row.get("qualification") == "valid"
        ]
        lines.append(
            f"| {harness['harness_id']} | {harness['valid_trials']} valid / "
            f"{harness['invalid_trials']} invalid / {harness['unavailable_trials']} unavailable | "
            f"{', '.join(str(score) for score in scores) or '—'} | "
            f"{_cell(harness['mean_outcome'])} | {_cell(harness['population_stddev'])} | "
            f"{_cell(harness['mean_elapsed_seconds'])} | "
            f"{_cell(harness['tool_invocations_observed_total'])} "
            f"({harness['tool_observation_coverage']}) |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- OpenCode and Hermes were highly repeatable on this task; OMP was somewhat lower and more variable.",
            "- Codex completed two excellent solutions but one valid migration failed with a foreign-key error, producing high variance.",
            "- NanoBot was unavailable because no qualified dedicated host OAuth profile existed; it was not scored zero.",
            "- The next highest-evidence run is the same frozen four-harness control across the remaining 11 DevHard tasks, after a clean-room auth lane is requalified or explicitly retained as a separate host stratum.",
            "",
        ]
    )
    return "\n".join(lines)


def _verify_private_manifest(root: Path, manifest: dict[str, Any]) -> list[Path]:
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), list):
        raise PilotEvidenceError("private pilot manifest is invalid")
    return _verify_records(root, manifest["files"])


def _verify_public_manifest(root: Path, manifest: dict[str, Any]) -> list[Path]:
    if manifest.get("schema_version") != 1 or not isinstance(
        manifest.get("artifacts"), list
    ):
        raise PilotEvidenceError("public pilot manifest is invalid")
    return _verify_records(root, manifest["artifacts"])


def _verify_records(root: Path, records: list[Any]) -> list[Path]:
    paths = []
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise PilotEvidenceError(f"manifest entry {index} is invalid")
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() in seen:
            raise PilotEvidenceError(f"unsafe or duplicate manifest path: {relative}")
        seen.add(relative.as_posix())
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise PilotEvidenceError(f"manifested artifact is missing: {relative}")
        raw = path.read_bytes()
        if record.get("sha256") != _sha256(raw) or record.get("bytes") != len(raw):
            raise PilotEvidenceError(f"manifested artifact changed: {relative}")
        paths.append(relative)
    return paths


def _write_public_manifest(root: Path) -> None:
    artifacts = []
    for path in _files_below(root):
        if path.name == "artifact-manifest.json":
            continue
        raw = path.read_bytes()
        artifacts.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(raw),
                "bytes": len(raw),
            }
        )
    _write_json(
        root / "artifact-manifest.json",
        {"schema_version": 1, "generated_at": _utc_now(), "artifacts": artifacts},
    )


def _runner_provenance(root: Path) -> dict[str, Any]:
    if not (root / ".git").exists():
        raise PilotEvidenceError(f"runner is not a Git worktree: {root}")
    commit = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise PilotEvidenceError("runner must be clean for commit-bound export")
    return {"commit": commit, "worktree_clean": True, "repository": "<RUNNER_ROOT>"}


def _redaction_roots(*paths: Path) -> list[tuple[str, str]]:
    candidates = [
        (str(paths[0]), "<SOURCE_EVIDENCE_ROOT>"),
        (str(paths[1]), "<SOURCE_EVIDENCE_ROOT>"),
        (str(paths[2]), "<RUNNER_ROOT>"),
        (str(paths[3]), "<RUNNER_ROOT>"),
        (str(Path.home()), "<HOME>"),
    ]
    selected: dict[str, str] = {}
    for value, placeholder in candidates:
        selected.setdefault(value, placeholder)
    return sorted(selected.items(), key=lambda item: len(item[0]), reverse=True)


def _sanitize_bytes(
    raw: bytes, replacements: Iterable[tuple[str, str]]
) -> tuple[bytes, dict[str, int]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw, {}
    counts: dict[str, int] = {}
    for value, placeholder in replacements:
        count = text.count(value)
        if count:
            text = text.replace(value, placeholder)
        counts[placeholder] = count
    text, encrypted_count = _PROVIDER_ENCRYPTED_FIELD.subn(
        lambda match: (
            match.group("prefix")
            + _PROVIDER_ENCRYPTED_REDACTION
            + match.group("suffix")
        ),
        text,
    )
    counts[_PROVIDER_ENCRYPTED_REDACTION] = encrypted_count
    return text.encode("utf-8"), counts


def _reject_secret_material(path: Path, raw: bytes) -> None:
    for name, pattern in _SECRET_PATTERNS.items():
        if pattern.search(raw):
            raise PilotEvidenceError(f"{name} pattern found in {path}")


def _json_lines(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _files_below(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise PilotEvidenceError(f"symbolic link is not publishable: {path}")
        if path.is_file():
            files.append(path)
    return files


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotEvidenceError(f"cannot read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise PilotEvidenceError(f"{label} must be a JSON object")
    return value


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sum_optional(*values: Any) -> int | None:
    numbers = [int(value) for value in values if isinstance(value, (int, float))]
    return sum(numbers) if numbers else None


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _cell(value: object) -> str:
    return "—" if value is None else str(value)

"""Fail-closed export and verification for public Highlander evidence bundles."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable


class EvidenceExportError(RuntimeError):
    """A source bundle cannot be published without weakening its evidence."""


_SECRET_PATTERNS = {
    "private_key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "github_token": re.compile(rb"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}"),
    "openai_key": re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    "bearer_token": re.compile(rb"Bearer [A-Za-z0-9._~-]{20,}"),
}


def export_public_bundle(
    source: str | Path,
    destination: str | Path,
    runner_repository: str | Path,
) -> dict[str, Any]:
    """Copy a sealed Match into a path-safe, self-verifying public bundle.

    The source manifest is verified before any copy. Only artifacts named by
    that manifest are exported; retained worktrees and workspaces therefore
    cannot leak into the public bundle. UTF-8 artifacts have machine-local
    roots replaced by stable placeholders, then a new manifest is generated.
    """

    source_supplied = Path(source).expanduser().absolute()
    source_root = source_supplied.resolve()
    destination_root = Path(destination).expanduser().resolve()
    runner_supplied = Path(runner_repository).expanduser().absolute()
    runner_root = runner_supplied.resolve()
    if not source_root.is_dir():
        raise EvidenceExportError(f"source Match directory does not exist: {source_root}")
    if destination_root.exists():
        raise EvidenceExportError(
            f"destination already exists; public bundles are immutable: {destination_root}"
        )
    if destination_root == source_root or source_root in destination_root.parents:
        raise EvidenceExportError("destination cannot be inside the source Match")

    source_manifest_path = source_root / "artifact-manifest.json"
    source_manifest = _load_json(source_manifest_path, "source artifact manifest")
    source_artifacts = _verify_manifest(source_root, source_manifest)
    execution_plan = _load_json(source_root / "execution-plan.json", "execution plan")
    match_result = _load_json(source_root / "match-result.json", "Match result")
    runner = _runner_provenance(runner_root)

    arena_value = execution_plan.get("arena", {}).get("repository")
    replacements = _redaction_roots(
        source_supplied=source_supplied,
        source_root=source_root,
        arena_value=arena_value if isinstance(arena_value, str) else None,
        runner_supplied=runner_supplied,
        runner_root=runner_root,
    )

    temporary = destination_root.with_name(destination_root.name + ".exporting")
    if temporary.exists():
        raise EvidenceExportError(f"stale temporary export exists: {temporary}")
    temporary.mkdir(parents=True)
    redaction_counts = {placeholder: 0 for _, placeholder in replacements}
    try:
        for relative in source_artifacts:
            source_path = source_root / relative
            destination_path = temporary / relative
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            raw = source_path.read_bytes()
            sanitized, counts = _sanitize_bytes(raw, replacements)
            _reject_secret_material(relative, sanitized)
            destination_path.write_bytes(sanitized)
            for placeholder, count in counts.items():
                redaction_counts[placeholder] += count

        public_provenance = {
            "schema_version": 1,
            "match_id": match_result.get("match_id"),
            "runner": runner,
            "arena": {
                "base_sha": execution_plan.get("arena", {}).get("base_sha"),
                "source_worktree_dirty": execution_plan.get("arena", {}).get(
                    "source_worktree_dirty"
                ),
            },
            "task_sha256": execution_plan.get("task", {}).get("sha256"),
            "plan_hash": execution_plan.get("plan_hash"),
            "source_artifact_manifest_sha256": _sha256(
                source_manifest_path.read_bytes()
            ),
            "claim_boundary": (
                "Quota-free fake Harness Adapter protocol qualification only. "
                "This bundle does not show a real coding harness solving T002 "
                "and must not be used as a performance ranking."
            ),
        }
        _write_json(temporary / "runner-provenance.json", public_provenance)
        _write_json(
            temporary / "redaction-report.json",
            {
                "schema_version": 1,
                "method": "exact-root replacement plus high-confidence secret scan",
                "replacements": [
                    {"placeholder": placeholder, "occurrences": redaction_counts[placeholder]}
                    for _, placeholder in replacements
                ],
                "secret_patterns_checked": sorted(_SECRET_PATTERNS),
                "raw_worktrees_exported": False,
            },
        )
        (temporary / "README.md").write_text(
            _bundle_readme(execution_plan, match_result, runner), encoding="utf-8"
        )
        report_path = temporary / "report" / "comparison.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            _comparison_report(execution_plan, match_result), encoding="utf-8"
        )

        for path in _files_below(temporary):
            raw = path.read_bytes()
            _reject_secret_material(path.relative_to(temporary), raw)
            for raw_root, _ in replacements:
                if raw_root.encode("utf-8") in raw:
                    raise EvidenceExportError(
                        f"redaction root remains in {path.relative_to(temporary)}"
                    )

        manifest = _build_manifest(
            temporary,
            generated_at=match_result.get("completed_at"),
            source_manifest_sha256=public_provenance[
                "source_artifact_manifest_sha256"
            ],
        )
        _write_json(temporary / "artifact-manifest.json", manifest)
        destination_root.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary, destination_root)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return verify_public_bundle(destination_root)


def verify_public_bundle(bundle: str | Path) -> dict[str, Any]:
    """Verify every public artifact against its regenerated manifest."""

    root = Path(bundle).expanduser().resolve()
    manifest = _load_json(root / "artifact-manifest.json", "public artifact manifest")
    artifacts = _verify_manifest(root, manifest)
    actual = {
        path.relative_to(root).as_posix()
        for path in _files_below(root)
        if path.name != "artifact-manifest.json"
    }
    expected = {path.as_posix() for path in artifacts}
    unexpected = sorted(actual - expected)
    if unexpected:
        raise EvidenceExportError(
            "public bundle contains unmanifested artifacts: " + ", ".join(unexpected)
        )
    return {
        "status": "verified",
        "bundle": str(root),
        "artifact_count": len(artifacts),
        "manifest_sha256": _sha256((root / "artifact-manifest.json").read_bytes()),
    }


def _runner_provenance(root: Path) -> dict[str, Any]:
    if not (root / ".git").exists():
        raise EvidenceExportError(f"runner repository is not a Git worktree: {root}")
    head = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise EvidenceExportError(
            "runner repository must be clean so the evidence is tied to one exact commit"
        )
    return {
        "commit": head,
        "worktree_clean": True,
        "repository": "<RUNNER_ROOT>",
    }


def _verify_manifest(root: Path, manifest: dict[str, Any]) -> list[Path]:
    if manifest.get("schema_version") != 1 or not isinstance(
        manifest.get("artifacts"), list
    ):
        raise EvidenceExportError("artifact manifest must be a schema_version 1 object")
    artifacts: list[Path] = []
    seen: set[str] = set()
    for index, record in enumerate(manifest["artifacts"]):
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise EvidenceExportError(f"artifact manifest entry {index} is invalid")
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() in seen:
            raise EvidenceExportError(f"unsafe or duplicate artifact path: {relative}")
        if relative.name == "artifact-manifest.json" or relative.parts[0] in {
            "worktrees",
            "workspaces",
        }:
            raise EvidenceExportError(f"non-publishable artifact path: {relative}")
        seen.add(relative.as_posix())
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise EvidenceExportError(f"manifested artifact is missing or unsafe: {relative}")
        raw = path.read_bytes()
        if record.get("sha256") != _sha256(raw) or record.get("bytes") != len(raw):
            raise EvidenceExportError(f"manifested artifact changed: {relative}")
        artifacts.append(relative)
    return artifacts


def _redaction_roots(
    *,
    source_supplied: Path,
    source_root: Path,
    arena_value: str | None,
    runner_supplied: Path,
    runner_root: Path,
) -> list[tuple[str, str]]:
    candidates = [
        (str(source_supplied), "<SOURCE_EVIDENCE_ROOT>"),
        (str(source_root), "<SOURCE_EVIDENCE_ROOT>"),
        (arena_value, "<ARENA_ROOT>") if arena_value else None,
        (str(Path(arena_value).resolve()), "<ARENA_ROOT>") if arena_value else None,
        (str(runner_supplied), "<RUNNER_ROOT>"),
        (str(runner_root), "<RUNNER_ROOT>"),
        (str(Path.home()), "<HOME>"),
    ]
    selected: dict[str, str] = {}
    for candidate in candidates:
        if candidate and candidate[0] not in selected:
            selected[candidate[0]] = candidate[1]
    return sorted(selected.items(), key=lambda item: len(item[0]), reverse=True)


def _sanitize_bytes(
    raw: bytes, replacements: Iterable[tuple[str, str]]
) -> tuple[bytes, dict[str, int]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw, {}
    counts: dict[str, int] = {}
    for source, placeholder in replacements:
        count = text.count(source)
        if count:
            text = text.replace(source, placeholder)
        counts[placeholder] = count
    return text.encode("utf-8"), counts


def _reject_secret_material(path: Path, raw: bytes) -> None:
    for name, pattern in _SECRET_PATTERNS.items():
        if pattern.search(raw):
            raise EvidenceExportError(f"{name} pattern found in {path}")


def _bundle_readme(
    plan: dict[str, Any], result: dict[str, Any], runner: dict[str, Any]
) -> str:
    trials = result.get("trials", [])
    qualified = sum(trial.get("qualification") == "qualified" for trial in trials)
    return (
        f"# {result.get('match_id')} evidence bundle\n\n"
        "This is a **zero-cost protocol qualification**, not a coding-harness "
        "performance result. Deterministic fake Harness Adapters received the exact "
        "T002 task bytes, crossed the same start gate, emitted control proof, and "
        "were reconciled by the parent MatchRunner. No model was called.\n\n"
        "| Proof | Value |\n"
        "|---|---|\n"
        f"| Runner commit | `{runner['commit']}` |\n"
        f"| Arena commit | `{plan.get('arena', {}).get('base_sha')}` |\n"
        f"| Task SHA-256 | `{plan.get('task', {}).get('sha256')}` |\n"
        f"| Plan SHA-256 | `{plan.get('plan_hash')}` |\n"
        f"| Qualified trials | {qualified} / {len(trials)} |\n"
        f"| Start skew | {result.get('start_skew_ms')} ms |\n\n"
        "The fake success/failure outcomes exercise evidence semantics; they do not "
        "mean that T002 was solved. See `report/comparison.md` for the explicit claim "
        "boundary and `runner-provenance.json` for commit linkage.\n\n"
        "From a Highlander checkout containing this bundle, verify every retained "
        "artifact with:\n\n"
        "```text\n"
        "python3 tools/evidence-bundle.py verify results/fake-t002-protocol-r1\n"
        "```\n"
    )


def _comparison_report(plan: dict[str, Any], result: dict[str, Any]) -> str:
    lines = [
        "# T002 quota-free protocol qualification",
        "",
        "> Claim boundary: this Match validates orchestration and retained evidence. "
        "It does not compare real harness capability or show T002 being solved.",
        "",
        "| Contender | Adapter | Qualification | Protocol outcome | Invalid reasons |",
        "|---|---|---|---|---|",
    ]
    adapters = {
        trial.get("contender_id"): trial.get("adapter")
        for trial in plan.get("trials", [])
    }
    for trial in result.get("trials", []):
        reasons = "; ".join(trial.get("invalid_reasons", [])) or "—"
        contender = trial.get("contender_id")
        lines.append(
            f"| {contender} | {adapters.get(contender)} | "
            f"{trial.get('qualification')} | {trial.get('competitive_outcome')} | {reasons} |"
        )
    lines.extend(
        [
            "",
            "## What this proves",
            "",
            "- one immutable task hash and arena commit were shared by every Trial;",
            "- prompt release used the all-ready start gate;",
            "- configured, runtime, and provider-wire control records were retained;",
            "- native and ATIF evidence, lifecycle events, outcomes, and cleanup "
            "proof were retained; and",
            "- the public copy excludes raw worktrees and machine-local paths.",
            "",
            "## What remains",
            "",
            "A decision-relevant result requires real, independently controlled "
            "Harness Adapters, deterministic T002 evaluation, repetitions, and a "
            "separately reviewed publication decision.",
            "",
        ]
    )
    return "\n".join(lines)


def _build_manifest(
    root: Path, *, generated_at: Any, source_manifest_sha256: str
) -> dict[str, Any]:
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
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "source_artifact_manifest_sha256": source_manifest_sha256,
        "artifacts": artifacts,
    }


def _files_below(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise EvidenceExportError(f"symbolic links are not publishable: {path}")
        if path.is_file():
            files.append(path)
    return files


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceExportError(f"could not read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceExportError(f"{label} must be a JSON object")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise EvidenceExportError(
            f"git {' '.join(args)} failed in runner repository: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

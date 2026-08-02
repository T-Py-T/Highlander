"""The deep MatchRunner module: plan once, execute a frozen local Match."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .adapters import adapter_for
from .model import HighlanderError, MatchSpec
from .sessions import session_adapter_for


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(canonical_json(value), encoding="utf-8")
    os.replace(temporary, path)


def append_event(path: Path, event: str, **details: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": utc_now(), "event": event, **details}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


class MatchRunner:
    """Own the Match transaction and keep adapters behind narrow seams."""

    def __init__(self, spec: MatchSpec):
        self.spec = spec

    @classmethod
    def from_file(cls, source: str | Path) -> "MatchRunner":
        return cls(MatchSpec.load(source))

    def doctor(self, session_override: str | None = None) -> dict[str, Any]:
        plan = self.plan(session_override=session_override)
        return {
            "match_id": self.spec.match_id,
            "ready_for_execution": all(
                trial["capability"]["execution_ready"] for trial in plan["trials"]
            )
            and plan["session"]["capability"]["available"],
            "session": plan["session"],
            "contenders": [
                {
                    "id": trial["contender_id"],
                    "adapter": trial["adapter"],
                    "capability": trial["capability"],
                }
                for trial in plan["trials"]
            ],
            "notes": [
                "No authentication, configuration, worktree, pane, or model call was changed.",
                "provider/wire proof is required for a strict result; weaker proof is provisional.",
            ],
        }

    def plan(self, session_override: str | None = None) -> dict[str, Any]:
        session_name = session_override or self.spec.session.adapter
        session_adapter = session_adapter_for(session_name)
        base_sha = self._git("rev-parse", f"{self.spec.arena.base_ref}^{{commit}}")
        task_bytes = self.spec.task.path.read_bytes()
        task_sha = sha256_bytes(task_bytes)
        run_dir = (self.spec.output_root / self.spec.match_id).resolve()
        source_dirty = bool(self._git("status", "--porcelain"))
        trials: list[dict[str, Any]] = []
        for contender in self.spec.contenders:
            trial_dir = run_dir / "trials" / contender.id / "attempt-001"
            worktree = run_dir / "worktrees" / contender.id / "attempt-001"
            adapter = adapter_for(contender.adapter)
            capability = adapter.probe(contender, self.spec.control_profile)
            invocation = adapter.invocation(
                contender,
                self.spec.control_profile,
                worktree,
                run_dir / "task" / "task.bin",
            )
            trials.append(
                {
                    "trial_id": f"{contender.id}-attempt-001",
                    "contender_id": contender.id,
                    "adapter": contender.adapter,
                    "options": contender.options,
                    "trial_dir": str(trial_dir),
                    "trial_plan_path": str(trial_dir / "trial-plan.json"),
                    "worktree": str(worktree),
                    "capability": capability,
                    "invocation": invocation,
                }
            )
        plan: dict[str, Any] = {
            "schema_version": 1,
            "match_id": self.spec.match_id,
            "lane": self.spec.lane,
            "run_dir": str(run_dir),
            "spec_hash": sha256_bytes(
                canonical_json(self.spec.as_dict()).encode("utf-8")
            ),
            "arena": {
                "repository": str(self.spec.arena.repository),
                "base_ref": self.spec.arena.base_ref,
                "base_sha": base_sha,
                "source_worktree_dirty": source_dirty,
            },
            "task": {
                "source": str(self.spec.task.path),
                "stored_path": str(run_dir / "task" / "task.bin"),
                "sha256": task_sha,
                "byte_length": len(task_bytes),
            },
            "control_profile": self.spec.as_dict()["control_profile"],
            "session": {
                "adapter": session_name,
                "capability": session_adapter.probe(),
                "concurrency": "all-ready filesystem gate",
            },
            "trials": trials,
            "safety": {
                "dry_run_default": True,
                "credentials_brokered": False,
                "paid_model_calls_in_plan": False,
                "worktrees_retained": True,
            },
        }
        plan["plan_hash"] = sha256_bytes(canonical_json(plan).encode("utf-8"))
        return plan

    def execute(
        self,
        reviewed_plan: dict[str, Any],
        session_override: str | None = None,
    ) -> dict[str, Any]:
        plan = self._verify_reviewed_plan(reviewed_plan, session_override)
        unavailable = [
            trial["contender_id"]
            for trial in plan["trials"]
            if not trial["capability"]["execution_ready"]
        ]
        if unavailable:
            raise HighlanderError(
                "execution is blocked until native adapters pass control verification: "
                + ", ".join(unavailable)
            )
        if not plan["session"]["capability"]["available"]:
            raise HighlanderError(
                f"Session Adapter is unavailable: {plan['session']['adapter']}"
            )

        run_dir = Path(plan["run_dir"])
        if run_dir.exists():
            raise HighlanderError(
                f"Match directory already exists; choose a new match_id: {run_dir}"
            )
        journal = run_dir / "journal" / "match-events.jsonl"
        task_bytes = self.spec.task.path.read_bytes()
        if sha256_bytes(task_bytes) != plan["task"]["sha256"]:
            raise HighlanderError("Task changed between planning and execution")

        run_dir.mkdir(parents=True)
        atomic_json(run_dir / "match-spec.json", self.spec.as_dict())
        atomic_json(run_dir / "execution-plan.json", plan)
        atomic_json(run_dir / "control-profile.json", plan["control_profile"])
        task_stored = Path(plan["task"]["stored_path"])
        task_stored.parent.mkdir(parents=True)
        task_stored.write_bytes(task_bytes)
        (task_stored.parent / "task.sha256").write_text(
            plan["task"]["sha256"] + "\n", encoding="utf-8"
        )
        append_event(journal, "PLANNED", plan_hash=plan["plan_hash"])
        append_event(journal, "PREFLIGHTED")

        workers: list[dict[str, Any]] = []
        session_adapter = session_adapter_for(plan["session"]["adapter"])
        handle = None
        cleanup: dict[str, Any] = {
            "session_closed": True,
            "session_started": False,
        }
        execution_error: str | None = None
        try:
            package_root = Path(__file__).resolve().parents[1]
            source_launcher = package_root / "tools" / "highlander.py"
            launcher_prefix = (
                [sys.executable, str(source_launcher)]
                if source_launcher.is_file()
                else [sys.executable, "-m", "highlander"]
            )
            for trial in plan["trials"]:
                worktree = Path(trial["worktree"])
                trial_dir = Path(trial["trial_dir"])
                worktree.parent.mkdir(parents=True, exist_ok=True)
                trial_dir.mkdir(parents=True, exist_ok=True)
                self._git(
                    "worktree",
                    "add",
                    "--detach",
                    str(worktree),
                    plan["arena"]["base_sha"],
                )
                trial_plan = {
                    **trial,
                    "match_id": plan["match_id"],
                    "lane": plan["lane"],
                    "task": plan["task"],
                    "control_profile": plan["control_profile"],
                    "start_gate": str(run_dir / "start-gate.json"),
                }
                atomic_json(Path(trial["trial_plan_path"]), trial_plan)
                atomic_json(trial_dir / "capability.json", trial["capability"])
                atomic_json(
                    trial_dir / "invocation.redacted.json", trial["invocation"]
                )
                workers.append(
                    {
                        "argv": [
                            *launcher_prefix,
                            "_worker",
                            "--trial-plan",
                            trial["trial_plan_path"],
                        ],
                        "cwd": str(worktree),
                        "terminal_log": str(
                            trial_dir / "native" / "terminal.log"
                        ),
                        "environment": self._worker_environment(),
                    }
                )
            append_event(journal, "PREPARED", trial_count=len(workers))
            handle = session_adapter.open(workers, plan["match_id"])
            atomic_json(run_dir / "session" / "manifest.json", handle.manifest())
            append_event(journal, "LAUNCHED", session=handle.manifest())
            self._wait_for_ready(plan, handle, session_adapter)
            append_event(journal, "ARMED")
            release = {"released_at": utc_now(), "released_ns": time.time_ns()}
            atomic_json(run_dir / "start-gate.json", release)
            append_event(journal, "RELEASED", **release)
            self._wait_for_outcomes(plan)
            append_event(journal, "COLLECTED")
        except Exception as exc:
            execution_error = str(exc)
            append_event(journal, "INVALID", reason=execution_error)
        finally:
            if handle is not None:
                cleanup = session_adapter.close(handle)
                cleanup["session_started"] = True
            atomic_json(run_dir / "session" / "cleanup.json", cleanup)

        results = []
        prompt_times: list[int] = []
        for trial in plan["trials"]:
            trial_dir = Path(trial["trial_dir"])
            worktree = Path(trial["worktree"])
            trial_dir.mkdir(parents=True, exist_ok=True)
            outcome_path = trial_dir / "outcome.json"
            if outcome_path.is_file():
                outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
                if isinstance(outcome.get("prompt_submitted_ns"), int):
                    prompt_times.append(outcome["prompt_submitted_ns"])
            else:
                outcome = {
                    "qualification": "invalid",
                    "competitive_outcome": "infrastructure_failure",
                    "invalid_reasons": [
                        execution_error or "worker outcome missing"
                    ],
                }
            repository_dir = trial_dir / "repository"
            repository_dir.mkdir(parents=True, exist_ok=True)
            if worktree.is_dir():
                status = self._git_at(worktree, "status", "--porcelain=v1")
                diff = self._git_at(
                    worktree, "diff", "--binary", plan["arena"]["base_sha"]
                )
                final_sha = self._git_at(worktree, "rev-parse", "HEAD")
            else:
                status = "worktree was not created"
                diff = ""
                final_sha = "unavailable"
            (repository_dir / "status.txt").write_text(
                status + ("\n" if status else ""), encoding="utf-8"
            )
            (repository_dir / "diff.patch").write_text(diff, encoding="utf-8")
            (repository_dir / "base-sha").write_text(
                plan["arena"]["base_sha"] + "\n", encoding="utf-8"
            )
            (repository_dir / "final-sha").write_text(final_sha + "\n", encoding="utf-8")
            trial_cleanup = {
                **self._reconcile_worker_identity(trial_dir),
                "session_reconciled": cleanup.get("session_closed", False),
                "worktree": str(worktree),
                "worktree_policy": "retained_intentionally_for_review",
            }
            atomic_json(trial_dir / "cleanup.json", trial_cleanup)
            outcome = self._audit_trial(plan, trial, outcome, trial_cleanup)
            atomic_json(outcome_path, outcome)
            results.append({"contender_id": trial["contender_id"], **outcome})

        start_skew_ms = (
            round((max(prompt_times) - min(prompt_times)) / 1_000_000, 3)
            if len(prompt_times) > 1
            else 0.0
        )
        match_result = {
            "match_id": plan["match_id"],
            "lane": plan["lane"],
            "state": "INVALID" if execution_error else "COMPLETE",
            "plan_hash": plan["plan_hash"],
            "task_sha256": plan["task"]["sha256"],
            "start_skew_ms": start_skew_ms,
            "session_cleanup": cleanup,
            "trials": results,
            "completed_at": utc_now(),
        }
        atomic_json(run_dir / "match-result.json", match_result)
        if execution_error:
            append_event(journal, "INVALID_SEALED")
        else:
            append_event(journal, "VERIFIED", start_skew_ms=start_skew_ms)
            append_event(journal, "COMPLETE")
        atomic_json(run_dir / "artifact-manifest.json", self._artifact_manifest(run_dir))
        if execution_error:
            raise HighlanderError(
                f"Match is invalid: {execution_error}. Evidence retained at {run_dir}"
            )
        return match_result

    def status(self, run_dir: str | Path) -> dict[str, Any]:
        root = Path(run_dir).expanduser().resolve()
        result = root / "match-result.json"
        if result.is_file():
            return json.loads(result.read_text(encoding="utf-8"))
        journal = root / "journal" / "match-events.jsonl"
        if not journal.is_file():
            raise HighlanderError(f"Not a Highlander Match directory: {root}")
        events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
        return {
            "match_id": root.name,
            "state": events[-1]["event"] if events else "UNKNOWN",
            "last_event": events[-1] if events else None,
        }

    def _wait_for_ready(
        self, plan: dict[str, Any], handle: Any, session_adapter: Any
    ) -> None:
        deadline = time.monotonic() + min(
            60, plan["control_profile"]["wall_time_seconds"]
        )
        ready_paths = [Path(trial["trial_dir"]) / "worker-ready.json" for trial in plan["trials"]]
        while time.monotonic() < deadline:
            if all(path.is_file() for path in ready_paths):
                return
            if failure := session_adapter.failure_before_ready(handle):
                raise HighlanderError(failure)
            time.sleep(0.05)
        missing = [str(path) for path in ready_paths if not path.is_file()]
        raise HighlanderError("workers did not become ready: " + ", ".join(missing))

    def _wait_for_outcomes(self, plan: dict[str, Any]) -> list[Path]:
        deadline = time.monotonic() + plan["control_profile"]["wall_time_seconds"]
        outcomes = [Path(trial["trial_dir"]) / "outcome.json" for trial in plan["trials"]]
        while time.monotonic() < deadline:
            if all(path.is_file() for path in outcomes):
                return outcomes
            time.sleep(0.05)
        missing = [str(path) for path in outcomes if not path.is_file()]
        raise HighlanderError("Match timed out waiting for outcomes: " + ", ".join(missing))

    def _artifact_manifest(self, root: Path) -> dict[str, Any]:
        artifacts = []
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(root)
            if path.name == "artifact-manifest.json" or relative.parts[0] == "worktrees":
                continue
            artifacts.append(
                {
                    "path": str(relative),
                    "sha256": sha256_bytes(path.read_bytes()),
                    "bytes": path.stat().st_size,
                }
            )
        return {"schema_version": 1, "generated_at": utc_now(), "artifacts": artifacts}

    def _verify_reviewed_plan(
        self, reviewed: dict[str, Any], session_override: str | None
    ) -> dict[str, Any]:
        if not isinstance(reviewed, dict):
            raise HighlanderError("reviewed plan must be a JSON object")
        claimed_hash = reviewed.get("plan_hash")
        unhashed = dict(reviewed)
        unhashed.pop("plan_hash", None)
        actual_hash = sha256_bytes(canonical_json(unhashed).encode("utf-8"))
        if claimed_hash != actual_hash:
            raise HighlanderError("reviewed plan hash is invalid")
        reviewed_session = reviewed.get("session", {}).get("adapter")
        if session_override and session_override != reviewed_session:
            raise HighlanderError(
                "Session Adapter override differs from the reviewed plan"
            )
        current = self.plan(session_override=reviewed_session)
        if canonical_json(reviewed) != canonical_json(current):
            raise HighlanderError(
                "Match inputs, base ref, Task, adapter versions, or capabilities changed after plan review"
            )
        return reviewed

    @staticmethod
    def _worker_environment() -> dict[str, str]:
        safe_names = (
            "LANG",
            "LC_ALL",
            "LC_CTYPE",
            "PATH",
            "SYSTEMROOT",
            "TMPDIR",
            "WINDIR",
        )
        environment = {
            name: os.environ[name] for name in safe_names if name in os.environ
        }
        environment["PYTHONUNBUFFERED"] = "1"
        return environment

    @staticmethod
    def _reconcile_worker_identity(trial_dir: Path) -> dict[str, Any]:
        ready_path = trial_dir / "worker-ready.json"
        if not ready_path.is_file():
            return {
                "process_reconciled": False,
                "process_identity_available": False,
                "unmanaged_resources_detected": True,
            }
        ready = json.loads(ready_path.read_text(encoding="utf-8"))
        process_group_id = ready.get("process_group_id")
        if os.name != "posix" or not isinstance(process_group_id, int):
            return {
                "process_reconciled": False,
                "process_identity_available": False,
                "unmanaged_resources_detected": True,
            }
        alive = _process_group_exists(process_group_id)
        if alive:
            try:
                os.killpg(process_group_id, signal.SIGTERM)
            except ProcessLookupError:
                alive = False
            deadline = time.monotonic() + 2
            while alive and time.monotonic() < deadline:
                time.sleep(0.05)
                alive = _process_group_exists(process_group_id)
        if alive:
            try:
                os.killpg(process_group_id, signal.SIGKILL)
            except ProcessLookupError:
                alive = False
            deadline = time.monotonic() + 2
            while alive and time.monotonic() < deadline:
                time.sleep(0.05)
                alive = _process_group_exists(process_group_id)
        return {
            "process_reconciled": not alive,
            "process_identity_available": True,
            "process_id": ready.get("process_id"),
            "process_group_id": process_group_id,
            "unmanaged_resources_detected": alive,
        }

    @staticmethod
    def _audit_trial(
        plan: dict[str, Any],
        trial: dict[str, Any],
        outcome: dict[str, Any],
        cleanup: dict[str, Any],
    ) -> dict[str, Any]:
        trial_dir = Path(trial["trial_dir"])
        control = plan["control_profile"]
        reasons = list(outcome.get("invalid_reasons", []))
        worker_claim = outcome.get("qualification")
        proof_files = {
            "configured": trial_dir / "configured-control.json",
            "runtime": trial_dir / "runtime-control.json",
            "provider_wire": trial_dir / "provider-control.json",
        }
        expected = {
            "model": control["requested_id"],
            "provider": control["provider_id"],
            "reasoning": control["reasoning_requested"],
        }
        for proof_name in control["proof_required"]:
            proof_path = proof_files[proof_name]
            if not proof_path.is_file():
                reasons.append(f"required {proof_name} control proof is missing")
                continue
            proof = json.loads(proof_path.read_text(encoding="utf-8"))
            if proof.get("verified") is not True:
                reasons.append(f"{proof_name} control proof is not verified")
            for field, expected_value in expected.items():
                if proof.get(field) != expected_value:
                    reasons.append(f"{proof_name} {field} diverged")
            if proof.get("fallback_events") != []:
                reasons.append(f"{proof_name} recorded fallback events")
            auxiliary = proof.get("auxiliary_models")
            if not isinstance(auxiliary, list) or any(
                model != control["requested_id"] for model in auxiliary
            ):
                reasons.append(f"{proof_name} auxiliary model proof diverged")
            if proof_name == "provider_wire":
                for field, expected_value in {
                    "upstream_id": control["upstream_id"],
                    "endpoint_or_deployment": control["endpoint_or_deployment"],
                    "region": control["region"],
                }.items():
                    if proof.get(field) != expected_value:
                        reasons.append(f"provider_wire {field} diverged")
        if outcome.get("task_sha256") != plan["task"]["sha256"]:
            reasons.append("outcome Task hash diverged")
        if not (trial_dir / "native" / "transcript.json").is_file():
            reasons.append("native transcript is missing")
        if not (trial_dir / "normalized" / "trajectory.atif.json").is_file():
            reasons.append("ATIF projection is missing")
        if not cleanup.get("process_reconciled"):
            reasons.append("worker process group was not reconciled")
        if not cleanup.get("session_reconciled"):
            reasons.append("session was not reconciled")
        events_path = trial_dir / "events.jsonl"
        if not events_path.is_file() or not events_path.read_text(
            encoding="utf-8"
        ).strip():
            reasons.append("Trial lifecycle events are missing")
        else:
            event_lines = events_path.read_text(encoding="utf-8").splitlines()
            final_event = json.loads(event_lines[-1]).get("event")
            if final_event not in {"QUALIFIED", "INVALID"}:
                reasons.append("Trial lifecycle did not reach a terminal evidence event")
        atif_path = trial_dir / "normalized" / "trajectory.atif.json"
        if atif_path.is_file():
            atif = json.loads(atif_path.read_text(encoding="utf-8"))
            if atif.get("schema_version") != "ATIF-v1.7":
                reasons.append("ATIF projection is not v1.7")
        if worker_claim == "invalid" and not reasons:
            reasons.append("worker invalidated the Trial without an auditable reason")

        audited = dict(outcome)
        audited["worker_qualification_claim"] = worker_claim
        audited["invalid_reasons"] = list(dict.fromkeys(reasons))
        audited["qualification"] = "invalid" if reasons else "qualified"
        audited["qualification_authority"] = "highlander-parent-audit-v1"
        return audited

    def _git(self, *args: str) -> str:
        return self._git_at(self.spec.arena.repository, *args)

    @staticmethod
    def _git_at(repository: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise HighlanderError(
                f"git {' '.join(args)} failed in {repository}: {result.stderr.strip()}"
            )
        return result.stdout.strip()


def run_worker(trial_plan_path: str | Path) -> int:
    """Internal worker process. It never receives credentials from Highlander."""

    plan_path = Path(trial_plan_path).expanduser().resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    trial_dir = Path(plan["trial_dir"])
    events = trial_dir / "events.jsonl"
    options = plan.get("options", {})
    if options.get("behavior") == "pre_gate_failure":
        append_event(events, "WORKER_FAILED_BEFORE_READY")
        return 3

    append_event(events, "WORKER_STARTED")
    atomic_json(
        trial_dir / "worker-ready.json",
        {
            "trial_id": plan["trial_id"],
            "ready_at": utc_now(),
            "process_id": os.getpid(),
            "process_group_id": os.getpgid(0) if os.name == "posix" else None,
        },
    )
    append_event(events, "ARMED")
    gate = Path(plan["start_gate"])
    deadline = time.monotonic() + plan["control_profile"]["wall_time_seconds"]
    while not gate.is_file():
        if time.monotonic() >= deadline:
            append_event(events, "START_GATE_TIMEOUT")
            return 4
        time.sleep(0.02)

    task_bytes = Path(plan["task"]["stored_path"]).read_bytes()
    observed_hash = sha256_bytes(task_bytes)
    if observed_hash != plan["task"]["sha256"]:
        outcome = {
            "qualification": "invalid",
            "competitive_outcome": "not_run",
            "invalid_reasons": ["Task hash mismatch"],
        }
        atomic_json(trial_dir / "outcome.json", outcome)
        return 5

    prompt_submitted_ns = time.time_ns()
    append_event(
        events,
        "TASK_SUBMITTED",
        task_sha256=observed_hash,
        submitted_ns=prompt_submitted_ns,
    )

    delay_ms = options.get("delay_ms", 0)
    if isinstance(delay_ms, int) and delay_ms > 0:
        time.sleep(min(delay_ms, 5000) / 1000)

    control = plan["control_profile"]
    configured = {
        "proof": "configured",
        "model": control["requested_id"],
        "provider": control["provider_id"],
        "reasoning": control["reasoning_requested"],
        "fallback_events": [],
        "auxiliary_models": [],
        "verified": True,
    }
    runtime = {**configured, "proof": "runtime"}
    provider = {
        **configured,
        "proof": "provider_wire",
        "upstream_id": control["upstream_id"],
        "endpoint_or_deployment": control["endpoint_or_deployment"],
        "region": control["region"],
    }
    if options.get("behavior") == "control_violation":
        runtime["model"] = "fake/divergent-model"
        runtime["verified"] = False
    atomic_json(trial_dir / "configured-control.json", configured)
    atomic_json(trial_dir / "runtime-control.json", runtime)
    atomic_json(trial_dir / "provider-control.json", provider)

    native_dir = trial_dir / "native"
    native_dir.mkdir(parents=True, exist_ok=True)
    transcript = {
        "format": "highlander-fake-native-v1",
        "task_sha256": observed_hash,
        "behavior": options.get("behavior", "success"),
        "message": "Deterministic fake harness completed without a model call.",
    }
    atomic_json(native_dir / "transcript.json", transcript)
    atif = {
        "schema_version": "ATIF-v1.7",
        "session_id": plan["trial_id"],
        "trajectory_id": plan["trial_id"],
        "agent": {
            "name": "highlander-fake",
            "version": "1",
            "model_name": control["upstream_id"],
            "extra": {"harness_adapter": "fake"},
        },
        "steps": [
            {
                "step_id": 1,
                "timestamp": utc_now(),
                "source": "user",
                "message": task_bytes.decode("utf-8", errors="replace"),
                "extra": {"sha256": observed_hash},
            },
            {
                "step_id": 2,
                "timestamp": utc_now(),
                "source": "agent",
                "model_name": control["upstream_id"],
                "message": transcript["message"],
                "llm_call_count": 0,
            },
        ],
        "final_metrics": {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost_usd": 0,
            "total_steps": 2,
        },
        "extra": {
            "native_evidence": "../native/transcript.json",
            "no_model_call": True,
        },
    }
    atomic_json(trial_dir / "normalized" / "trajectory.atif.json", atif)

    invalid_reasons = []
    if not runtime["verified"]:
        invalid_reasons.append("runtime model diverged from configured model")
    competitive = (
        "protocol_harness_failure"
        if options.get("behavior") == "harness_failure"
        else "protocol_success"
    )
    outcome = {
        "qualification": "invalid" if invalid_reasons else "qualified",
        "competitive_outcome": competitive,
        "invalid_reasons": invalid_reasons,
        "task_sha256": observed_hash,
        "prompt_submitted_ns": prompt_submitted_ns,
        "model_calls": 0,
        "cost": 0,
    }
    append_event(events, "EVIDENCE_COLLECTED")
    append_event(events, "QUALIFIED" if not invalid_reasons else "INVALID")
    # Outcome is the final atomic worker write. Its presence therefore proves
    # that all preceding evidence and lifecycle records were flushed.
    atomic_json(trial_dir / "outcome.json", outcome)
    return 0


def _process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True

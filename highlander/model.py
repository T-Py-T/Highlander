"""Validated domain objects for a Highlander Match."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
LANES = {
    "controlled_efficacy",
    "concurrency",
    "subscription_realism",
    "warm_memory",
}
SESSION_ADAPTERS = {"headless", "tmux"}


class HighlanderError(RuntimeError):
    """Base error for an actionable Highlander failure."""


class SpecError(HighlanderError):
    """The Match specification is incomplete or unsafe."""


@dataclass(frozen=True)
class ArenaSpec:
    repository: Path
    base_ref: str


@dataclass(frozen=True)
class TaskSpec:
    path: Path


@dataclass(frozen=True)
class ControlProfile:
    requested_id: str
    upstream_id: str
    provider_id: str
    endpoint_or_deployment: str
    region: str
    auth_route: str
    reasoning_requested: str
    wire_parameter: str
    fallback_policy: str
    auxiliary_model_policy: str
    wall_time_seconds: int
    external_model_request_cap: int | None
    proof_required: tuple[str, ...]


@dataclass(frozen=True)
class ContenderSpec:
    id: str
    adapter: str
    options: dict[str, Any]


@dataclass(frozen=True)
class SessionSpec:
    adapter: str


@dataclass(frozen=True)
class MatchSpec:
    schema_version: int
    match_id: str
    lane: str
    arena: ArenaSpec
    task: TaskSpec
    control_profile: ControlProfile
    contenders: tuple[ContenderSpec, ...]
    session: SessionSpec
    output_root: Path
    source_path: Path

    @classmethod
    def load(cls, source: str | Path) -> "MatchSpec":
        source_path = Path(source).expanduser().resolve()
        if not source_path.is_file():
            raise SpecError(f"Match specification not found: {source_path}")
        try:
            raw = json.loads(source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SpecError(f"Invalid Match JSON: {exc}") from exc
        if not isinstance(raw, dict):
            raise SpecError("Match specification must be a JSON object")

        root = source_path.parent
        schema_version = raw.get("schema_version")
        if schema_version != 1:
            raise SpecError("schema_version must be 1")

        match_id = _required_text(raw, "match_id")
        if not SAFE_ID.fullmatch(match_id):
            raise SpecError("match_id must be a safe 1-64 character identifier")

        lane = _required_text(raw, "lane")
        if lane not in LANES:
            raise SpecError(f"lane must be one of: {', '.join(sorted(LANES))}")

        arena_raw = _required_object(raw, "arena")
        repository = _resolve(root, _required_text(arena_raw, "repository"))
        if not repository.is_dir() or not (
            (repository / ".git").is_dir() or (repository / ".git").is_file()
        ):
            raise SpecError(f"Arena is not a Git worktree: {repository}")
        arena = ArenaSpec(
            repository=repository,
            base_ref=_required_text(arena_raw, "base_ref"),
        )

        task_raw = _required_object(raw, "task")
        task_path = _resolve(root, _required_text(task_raw, "path"))
        if not task_path.is_file():
            raise SpecError(f"Task file not found: {task_path}")
        task = TaskSpec(path=task_path)

        control_raw = _required_object(raw, "control_profile")
        model_raw = _required_object(control_raw, "model")
        reasoning_raw = _required_object(control_raw, "reasoning")
        limits_raw = control_raw.get("limits", {})
        if not isinstance(limits_raw, dict):
            raise SpecError("control_profile.limits must be an object")
        wall_time = limits_raw.get("wall_time_seconds", 1800)
        if not isinstance(wall_time, int) or not 1 <= wall_time <= 86400:
            raise SpecError("wall_time_seconds must be an integer from 1 to 86400")
        request_cap = limits_raw.get("external_model_request_cap")
        if request_cap is not None and (
            not isinstance(request_cap, int) or request_cap < 1
        ):
            raise SpecError("external_model_request_cap must be a positive integer")
        proof_required = control_raw.get(
            "proof_required", ["configured", "runtime", "provider_wire"]
        )
        if not isinstance(proof_required, list) or not all(
            item in {"configured", "runtime", "provider_wire"}
            for item in proof_required
        ):
            raise SpecError(
                "proof_required may contain configured, runtime, and provider_wire"
            )
        control = ControlProfile(
            requested_id=_required_text(model_raw, "requested_id"),
            upstream_id=_required_text(model_raw, "upstream_id"),
            provider_id=_required_text(model_raw, "provider_id"),
            endpoint_or_deployment=_required_text(
                model_raw, "endpoint_or_deployment"
            ),
            region=_required_text(model_raw, "region"),
            auth_route=_required_text(model_raw, "auth_route"),
            reasoning_requested=_required_text(reasoning_raw, "requested"),
            wire_parameter=_required_text(reasoning_raw, "wire_parameter"),
            fallback_policy=_required_text(control_raw, "fallback_policy"),
            auxiliary_model_policy=_required_text(
                control_raw, "auxiliary_model_policy"
            ),
            wall_time_seconds=wall_time,
            external_model_request_cap=request_cap,
            proof_required=tuple(proof_required),
        )
        if control.fallback_policy != "forbidden":
            raise SpecError("the pilot requires fallback_policy=forbidden")
        if control.auxiliary_model_policy not in {"disabled", "same_model"}:
            raise SpecError(
                "auxiliary_model_policy must be disabled or same_model"
            )

        contenders_raw = raw.get("contenders")
        if not isinstance(contenders_raw, list) or len(contenders_raw) < 2:
            raise SpecError("contenders must contain at least two entries")
        contenders: list[ContenderSpec] = []
        seen: set[str] = set()
        for index, contender_raw in enumerate(contenders_raw):
            if not isinstance(contender_raw, dict):
                raise SpecError(f"contenders[{index}] must be an object")
            contender_id = _required_text(contender_raw, "id")
            if not SAFE_ID.fullmatch(contender_id):
                raise SpecError(f"unsafe contender id: {contender_id}")
            if contender_id in seen:
                raise SpecError(f"duplicate contender id: {contender_id}")
            seen.add(contender_id)
            options = contender_raw.get("options", {})
            if not isinstance(options, dict):
                raise SpecError(f"options for {contender_id} must be an object")
            _reject_secret_keys(options, f"contenders[{index}].options")
            contenders.append(
                ContenderSpec(
                    id=contender_id,
                    adapter=_required_text(contender_raw, "adapter"),
                    options=options,
                )
            )

        session_raw = raw.get("session", {"adapter": "headless"})
        if not isinstance(session_raw, dict):
            raise SpecError("session must be an object")
        session_adapter = _required_text(session_raw, "adapter")
        if session_adapter not in SESSION_ADAPTERS:
            raise SpecError(
                f"session.adapter must be one of: {', '.join(sorted(SESSION_ADAPTERS))}"
            )
        session = SessionSpec(adapter=session_adapter)

        output_value = raw.get("output_root")
        output_root = (
            _resolve(root, output_value)
            if isinstance(output_value, str) and output_value
            else repository.parent / "highlander-runs"
        )

        return cls(
            schema_version=schema_version,
            match_id=match_id,
            lane=lane,
            arena=arena,
            task=task,
            control_profile=control,
            contenders=tuple(contenders),
            session=session,
            output_root=output_root,
            source_path=source_path,
        )

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["arena"]["repository"] = str(self.arena.repository)
        value["task"]["path"] = str(self.task.path)
        value["output_root"] = str(self.output_root)
        value["source_path"] = str(self.source_path)
        value["control_profile"]["proof_required"] = list(
            self.control_profile.proof_required
        )
        value["contenders"] = [asdict(item) for item in self.contenders]
        return value


def _required_object(parent: dict[str, Any], name: str) -> dict[str, Any]:
    value = parent.get(name)
    if not isinstance(value, dict):
        raise SpecError(f"{name} must be an object")
    return value


def _required_text(parent: dict[str, Any], name: str) -> str:
    value = parent.get(name)
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{name} must be a non-empty string")
    return value


def _resolve(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def _reject_secret_keys(value: Any, location: str) -> None:
    secret_markers = {
        "api_key",
        "access_key",
        "credential",
        "oauth",
        "password",
        "private_key",
        "secret",
        "token",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(marker in normalized for marker in secret_markers):
                raise SpecError(
                    f"{location}.{key} looks credential-bearing; Match specs may record route names but never secret values"
                )
            _reject_secret_keys(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_keys(child, f"{location}[{index}]")

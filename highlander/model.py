"""Validated domain objects for a Highlander Match."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
PINNED_IMAGE = re.compile(
    r"^(?:[A-Za-z0-9][A-Za-z0-9._/:.-]*@)?sha256:[0-9a-f]{64}$"
)
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
class CleanRoomSpec:
    runtime: str
    profile: str
    evaluator_image: str
    network: str
    cpus: float
    memory_mb: int
    pids_limit: int
    tmpfs_mb: int
    retain_workspaces: bool


@dataclass(frozen=True)
class ArenaSpec:
    repository: Path
    base_ref: str
    clean_room: CleanRoomSpec | None


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
class EvaluationCommandSpec:
    id: str
    argv: tuple[str, ...]
    timeout_seconds: int


@dataclass(frozen=True)
class EvaluationSpec:
    commands: tuple[EvaluationCommandSpec, ...]
    overlay: Path | None


@dataclass(frozen=True)
class MatchSpec:
    schema_version: int
    match_id: str
    lane: str
    arena: ArenaSpec
    task: TaskSpec
    control_profile: ControlProfile
    contenders: tuple[ContenderSpec, ...]
    evaluation: EvaluationSpec | None
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
        clean_room = _load_clean_room(arena_raw.get("clean_room"))
        arena = ArenaSpec(
            repository=repository,
            base_ref=_required_text(arena_raw, "base_ref"),
            clean_room=clean_room,
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
            adapter_name = _required_text(contender_raw, "adapter")
            options = contender_raw.get("options", {})
            if not isinstance(options, dict):
                raise SpecError(f"options for {contender_id} must be an object")
            _reject_secret_keys(options, f"contenders[{index}].options")
            options = _validated_options(adapter_name, options, contender_id)
            contenders.append(
                ContenderSpec(
                    id=contender_id,
                    adapter=adapter_name,
                    options=options,
                )
            )

        if clean_room:
            missing_images = [
                contender.id
                for contender in contenders
                if not isinstance(contender.options.get("image"), str)
            ]
            if missing_images:
                raise SpecError(
                    "clean-room contenders require a pinned image: "
                    + ", ".join(missing_images)
                )
        elif any("image" in contender.options for contender in contenders):
            raise SpecError(
                "contender images require arena.clean_room so host configuration cannot leak into a Trial"
            )

        evaluation = _load_evaluation(raw.get("evaluation"), root)
        if clean_room and evaluation is None:
            raise SpecError("clean-room Matches require deterministic evaluation.commands")

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
            evaluation=evaluation,
            session=session,
            output_root=output_root,
            source_path=source_path,
        )

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["arena"]["repository"] = str(self.arena.repository)
        if self.arena.clean_room is None:
            value["arena"].pop("clean_room", None)
        value["task"]["path"] = str(self.task.path)
        value["output_root"] = str(self.output_root)
        value["source_path"] = str(self.source_path)
        value["control_profile"]["proof_required"] = list(
            self.control_profile.proof_required
        )
        value["contenders"] = [asdict(item) for item in self.contenders]
        if self.evaluation:
            evaluation_value: dict[str, Any] = {
                "commands": [asdict(item) for item in self.evaluation.commands]
            }
            if self.evaluation.overlay:
                evaluation_value["overlay"] = str(self.evaluation.overlay)
            value["evaluation"] = evaluation_value
        else:
            value.pop("evaluation", None)
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
        "authorization",
        "bearer",
        "cookie",
        "credential",
        "header",
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


def _validated_options(
    adapter: str, options: dict[str, Any], contender_id: str
) -> dict[str, Any]:
    allowed = {
        "fake": {"behavior", "delay_ms", "tools"},
        "omp": {"approval_mode", "profile", "image", "seed_profile"},
        "opencode": {"pure", "image", "seed_profile"},
        "codex": {"image", "seed_profile"},
        "hermes": {"image", "seed_profile"},
        "nanobot": {"image", "seed_profile"},
    }
    if adapter not in allowed:
        if options:
            raise SpecError(
                f"unknown adapter {adapter!r} cannot accept serialized options"
            )
        return {}
    unexpected = sorted(set(options) - allowed[adapter])
    if unexpected:
        raise SpecError(
            f"unsupported options for {contender_id}/{adapter}: {', '.join(unexpected)}"
        )

    validated = dict(options)
    image = validated.get("image")
    if image is not None and (
        not isinstance(image, str) or not PINNED_IMAGE.fullmatch(image)
    ):
        raise SpecError(
            f"{contender_id} image must be a pinned image ID or repository digest"
        )
    seed_profile = validated.get("seed_profile")
    if seed_profile is not None and (
        not isinstance(seed_profile, str) or not SAFE_ID.fullmatch(seed_profile)
    ):
        raise SpecError(f"{contender_id} seed_profile must be a safe identifier")
    if adapter == "fake":
        behavior = validated.get("behavior", "success")
        if behavior not in {
            "success",
            "harness_failure",
            "control_violation",
            "pre_gate_failure",
        }:
            raise SpecError(f"unsupported fake behavior: {behavior}")
        delay = validated.get("delay_ms", 0)
        if not isinstance(delay, int) or not 0 <= delay <= 5000:
            raise SpecError("fake delay_ms must be an integer from 0 to 5000")
        tools = validated.get("tools", ["read", "edit", "test"])
        if not isinstance(tools, list) or not all(
            isinstance(tool, str) and SAFE_ID.fullmatch(tool) for tool in tools
        ):
            raise SpecError("fake tools must be safe string identifiers")
        validated.update({"behavior": behavior, "delay_ms": delay, "tools": tools})
    elif adapter == "omp":
        approval = validated.get("approval_mode", "write")
        if approval not in {"always-ask", "write", "yolo"}:
            raise SpecError("OMP approval_mode must be always-ask, write, or yolo")
        validated["approval_mode"] = approval
        if profile := validated.get("profile"):
            if not isinstance(profile, str) or not SAFE_ID.fullmatch(profile):
                raise SpecError("OMP profile must be a safe identifier")
    elif adapter == "opencode":
        pure = validated.get("pure", True)
        if not isinstance(pure, bool):
            raise SpecError("OpenCode pure must be boolean")
        validated["pure"] = pure
    return validated


def _load_clean_room(value: Any) -> CleanRoomSpec | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SpecError("arena.clean_room must be an object")
    allowed = {
        "runtime",
        "profile",
        "evaluator_image",
        "network",
        "cpus",
        "memory_mb",
        "pids_limit",
        "tmpfs_mb",
        "retain_workspaces",
    }
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise SpecError(
            "unsupported arena.clean_room fields: " + ", ".join(unexpected)
        )
    runtime = _required_text(value, "runtime")
    if runtime not in {"docker", "podman"}:
        raise SpecError("arena.clean_room.runtime must be docker or podman")
    profile = _required_text(value, "profile")
    if profile not in {"clean-core", "production-stack", "plugin-ablation"}:
        raise SpecError(
            "arena.clean_room.profile must be clean-core, production-stack, or plugin-ablation"
        )
    evaluator_image = _required_text(value, "evaluator_image")
    if not PINNED_IMAGE.fullmatch(evaluator_image):
        raise SpecError("arena.clean_room.evaluator_image must be a pinned image")
    network = value.get("network", "bridge")
    if not isinstance(network, str) or not SAFE_ID.fullmatch(network):
        raise SpecError("arena.clean_room.network must be a safe runtime network name")
    if network == "host" or network.startswith("container"):
        raise SpecError("clean-room Matches cannot use host or container-shared networking")
    cpus = value.get("cpus", 2)
    if not isinstance(cpus, (int, float)) or isinstance(cpus, bool) or not 0.25 <= cpus <= 64:
        raise SpecError("arena.clean_room.cpus must be from 0.25 to 64")
    memory_mb = _bounded_integer(value, "memory_mb", 4096, 256, 131072)
    pids_limit = _bounded_integer(value, "pids_limit", 512, 64, 4096)
    tmpfs_mb = _bounded_integer(value, "tmpfs_mb", 1024, 64, 16384)
    retain = value.get("retain_workspaces", False)
    if not isinstance(retain, bool):
        raise SpecError("arena.clean_room.retain_workspaces must be boolean")
    return CleanRoomSpec(
        runtime=runtime,
        profile=profile,
        evaluator_image=evaluator_image,
        network=network,
        cpus=float(cpus),
        memory_mb=memory_mb,
        pids_limit=pids_limit,
        tmpfs_mb=tmpfs_mb,
        retain_workspaces=retain,
    )


def _load_evaluation(value: Any, root: Path) -> EvaluationSpec | None:
    if value is None:
        return None
    if not isinstance(value, dict) or not set(value).issubset({"commands", "overlay"}):
        raise SpecError("evaluation may contain only commands and overlay")
    commands_raw = value.get("commands")
    if not isinstance(commands_raw, list) or not commands_raw:
        raise SpecError("evaluation.commands must be a non-empty list")
    commands: list[EvaluationCommandSpec] = []
    seen: set[str] = set()
    for index, command in enumerate(commands_raw):
        if not isinstance(command, dict) or not set(command).issubset(
            {"id", "argv", "timeout_seconds"}
        ):
            raise SpecError(f"evaluation.commands[{index}] has unsupported fields")
        command_id = _required_text(command, "id")
        if not SAFE_ID.fullmatch(command_id) or command_id in seen:
            raise SpecError(f"unsafe or duplicate evaluation command id: {command_id}")
        seen.add(command_id)
        argv = command.get("argv")
        if not isinstance(argv, list) or not argv or not all(
            isinstance(item, str) and item and "\x00" not in item for item in argv
        ):
            raise SpecError(
                f"evaluation.commands[{index}].argv must be a non-empty argv array"
            )
        timeout = _bounded_integer(command, "timeout_seconds", 300, 1, 3600)
        commands.append(
            EvaluationCommandSpec(
                id=command_id, argv=tuple(argv), timeout_seconds=timeout
            )
        )
    overlay_value = value.get("overlay")
    overlay = None
    if overlay_value is not None:
        if not isinstance(overlay_value, str) or not overlay_value:
            raise SpecError("evaluation.overlay must be a directory path")
        overlay = _resolve(root, overlay_value)
        if not overlay.is_dir():
            raise SpecError(f"evaluation overlay directory not found: {overlay}")
        if any(path.is_symlink() for path in overlay.rglob("*")):
            raise SpecError("evaluation overlays cannot contain symbolic links")
    return EvaluationSpec(commands=tuple(commands), overlay=overlay)


def _bounded_integer(
    parent: dict[str, Any], name: str, default: int, minimum: int, maximum: int
) -> int:
    value = parent.get(name, default)
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise SpecError(f"{name} must be an integer from {minimum} to {maximum}")
    return value

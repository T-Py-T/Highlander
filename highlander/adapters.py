"""Harness Adapter implementations and their fail-closed capability probes."""

from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .model import ContenderSpec, ControlProfile, HighlanderError


class HarnessAdapter(ABC):
    """Internal SPI for harness-specific controls and native evidence."""

    name: str

    @abstractmethod
    def probe(
        self, contender: ContenderSpec, control: ControlProfile
    ) -> dict[str, Any]:
        """Return capabilities without changing authentication or configuration."""

    @abstractmethod
    def invocation(
        self,
        contender: ContenderSpec,
        control: ControlProfile,
        worktree: Path,
        task_path: Path,
    ) -> dict[str, Any]:
        """Return a redacted, inspectable native launch plan."""


class FakeHarnessAdapter(HarnessAdapter):
    name = "fake"

    def probe(
        self, contender: ContenderSpec, control: ControlProfile
    ) -> dict[str, Any]:
        return {
            "harness": {"name": "fake", "version": "1"},
            "execution_implemented": True,
            "execution_ready": True,
            "protocol": "highlander-fake-v1",
            "prompt_transport": "exact-bytes",
            "control_proof": {
                "configured": True,
                "runtime": True,
                "provider_wire": True,
            },
            "tools": list(contender.options.get("tools", ["read", "edit", "test"])),
            "mcp_servers": [],
            "memory": {"mode": "none", "scope": "trial", "seeded": False},
            "permissions": "fixture-only",
            "subagents": {"enabled": False},
            "limitations": ["deterministic test double; not a coding harness"],
        }

    def invocation(
        self,
        contender: ContenderSpec,
        control: ControlProfile,
        worktree: Path,
        task_path: Path,
    ) -> dict[str, Any]:
        return {
            "argv": ["<internal:fake-harness>"],
            "cwd": str(worktree),
            "protocol": "highlander-fake-v1",
            "prompt_transport": "exact-bytes",
            "inherited_environment_names": [],
            "credential_values_recorded": False,
        }


class OmpHarnessAdapter(HarnessAdapter):
    name = "omp"

    def probe(
        self, contender: ContenderSpec, control: ControlProfile
    ) -> dict[str, Any]:
        binary = shutil.which("omp")
        return {
            "harness": {"name": "oh-my-pi", "version": _version(binary)},
            "binary": binary,
            "execution_implemented": True,
            "execution_ready": False,
            "execution_requires": "digest-pinned OCI clean room",
            "protocol": "omp-rpc",
            "prompt_transport": "rpc-exact-message",
            "control_proof": {
                "configured": True,
                "runtime": True,
                "provider_wire": False,
            },
            "tools": ["native OMP toolset; capture required at execution"],
            "mcp_servers": ["capture required at execution"],
            "memory": {"mode": "isolated-profile-required", "scope": "trial"},
            "permissions": contender.options.get("approval_mode", "write"),
            "subagents": {"policy": control.auxiliary_model_policy},
            "limitations": [
                "host execution is blocked; native execution requires a clean-room image",
                "provider/wire proof is unavailable on ordinary subscription routes",
            ],
        }

    def invocation(
        self,
        contender: ContenderSpec,
        control: ControlProfile,
        worktree: Path,
        task_path: Path,
    ) -> dict[str, Any]:
        argv = [
            "omp",
            "--print",
            "--mode",
            "json",
            "--cwd",
            str(worktree),
            "--model",
            control.requested_id,
            "--thinking",
            control.reasoning_requested,
            "--smol",
            control.requested_id,
            "--slow",
            control.requested_id,
            "--plan",
            control.requested_id,
            "--no-prewalk",
            "--no-title",
            "--no-session",
            "--no-extensions",
            "--no-skills",
            "--no-rules",
            "--max-time",
            f"{control.wall_time_seconds}s",
            "--approval-mode",
            contender.options.get("approval_mode", "write"),
        ]
        if profile := contender.options.get("profile"):
            argv.extend(["--profile", str(profile)])
        return {
            "argv": argv,
            "cwd": str(worktree),
            "protocol": "omp-json",
            "prompt_transport": "exact Task UTF-8 appended as one argv element after start gate",
            "task_sha_source": str(task_path),
            "inherited_environment_names": [],
            "credential_values_recorded": False,
        }


class OpenCodeHarnessAdapter(HarnessAdapter):
    name = "opencode"

    def probe(
        self, contender: ContenderSpec, control: ControlProfile
    ) -> dict[str, Any]:
        binary = shutil.which("opencode")
        return {
            "harness": {"name": "opencode", "version": _version(binary)},
            "binary": binary,
            "execution_implemented": True,
            "execution_ready": False,
            "execution_requires": "digest-pinned OCI clean room",
            "protocol": "opencode-json",
            "prompt_transport": "argv-exact-string",
            "control_proof": {
                "configured": True,
                "runtime": True,
                "provider_wire": False,
            },
            "tools": ["native OpenCode toolset; capture required at execution"],
            "mcp_servers": ["capture required at execution"],
            "memory": {"mode": "isolated-config-required", "scope": "trial"},
            "permissions": "native policy; freeze before execution",
            "subagents": {"policy": control.auxiliary_model_policy},
            "limitations": [
                "host execution is blocked; native execution requires a clean-room image",
                "reasoning variants are provider-specific",
                "provider/wire proof is unavailable on ordinary subscription routes",
            ],
        }

    def invocation(
        self,
        contender: ContenderSpec,
        control: ControlProfile,
        worktree: Path,
        task_path: Path,
    ) -> dict[str, Any]:
        argv = [
            "opencode",
            "run",
            "--format",
            "json",
            "--dir",
            str(worktree),
            "--model",
            control.requested_id,
            "--variant",
            control.reasoning_requested,
            "--auto",
        ]
        if contender.options.get("pure", True):
            argv.append("--pure")
        return {
            "argv": argv,
            "cwd": str(worktree),
            "protocol": "opencode-json",
            "prompt_transport": "exact Task string appended as one argv element",
            "task_sha_source": str(task_path),
            "inherited_environment_names": [],
            "credential_values_recorded": False,
        }


class CodexHarnessAdapter(HarnessAdapter):
    name = "codex"

    def probe(
        self, contender: ContenderSpec, control: ControlProfile
    ) -> dict[str, Any]:
        binary = shutil.which("codex")
        return {
            "harness": {"name": "codex", "version": _version(binary)},
            "binary": binary,
            "execution_implemented": True,
            "execution_ready": False,
            "execution_requires": "digest-pinned OCI clean room",
            "protocol": "codex-jsonl",
            "prompt_transport": "argv-exact-string",
            "control_proof": {
                "configured": True,
                "runtime": True,
                "provider_wire": False,
            },
            "tools": ["native Codex toolset; capture required at execution"],
            "mcp_servers": [],
            "memory": {"mode": "ephemeral", "scope": "trial", "seeded": False},
            "permissions": "container boundary with non-interactive full workspace access",
            "subagents": {"policy": control.auxiliary_model_policy},
            "limitations": [
                "host execution is blocked; native execution requires a clean-room image",
                "subscription provider/wire proof depends on native JSONL evidence",
            ],
        }

    def invocation(
        self,
        contender: ContenderSpec,
        control: ControlProfile,
        worktree: Path,
        task_path: Path,
    ) -> dict[str, Any]:
        return {
            "argv": [
                "codex",
                "exec",
                "--json",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--dangerously-bypass-approvals-and-sandbox",
                "--cd",
                str(worktree),
                "--model",
                control.requested_id,
                "--config",
                f'model_reasoning_effort="{control.wire_parameter}"',
                "--config",
                'cli_auth_credentials_store="file"',
            ],
            "cwd": str(worktree),
            "protocol": "codex-jsonl",
            "prompt_transport": "exact Task string appended as one argv element",
            "task_sha_source": str(task_path),
            "inherited_environment_names": [],
            "credential_values_recorded": False,
        }


class HermesHarnessAdapter(HarnessAdapter):
    name = "hermes"

    def probe(
        self, contender: ContenderSpec, control: ControlProfile
    ) -> dict[str, Any]:
        binary = shutil.which("hermes")
        return {
            "harness": {"name": "hermes-agent", "version": _version(binary)},
            "binary": binary,
            "execution_implemented": True,
            "execution_ready": False,
            "execution_requires": "digest-pinned OCI clean room",
            "protocol": "hermes-oneshot",
            "prompt_transport": "argv-exact-string",
            "control_proof": {
                "configured": True,
                "runtime": True,
                "provider_wire": False,
            },
            "tools": ["native Hermes clean-core toolset; capture required at execution"],
            "mcp_servers": [],
            "memory": {"mode": "safe-mode fresh home", "scope": "trial"},
            "permissions": "container boundary with Hermes yolo mode",
            "subagents": {"policy": control.auxiliary_model_policy},
            "limitations": [
                "safe mode disables user plugins, memories, rules, and MCP servers",
                "subscription provider/wire proof requires a post-run usage projection",
            ],
        }

    def invocation(
        self,
        contender: ContenderSpec,
        control: ControlProfile,
        worktree: Path,
        task_path: Path,
    ) -> dict[str, Any]:
        return {
            "argv": [
                "hermes",
                "--model",
                control.requested_id,
                "--provider",
                control.provider_id,
                "--reasoning",
                control.wire_parameter,
                "--yolo",
                "--safe-mode",
                "--oneshot",
            ],
            "cwd": str(worktree),
            "protocol": "hermes-oneshot",
            "prompt_transport": "exact Task string appended after --oneshot",
            "task_sha_source": str(task_path),
            "inherited_environment_names": [],
            "credential_values_recorded": False,
        }


class NanoBotHarnessAdapter(HarnessAdapter):
    name = "nanobot"

    def probe(
        self, contender: ContenderSpec, control: ControlProfile
    ) -> dict[str, Any]:
        binary = shutil.which("nanobot")
        return {
            "harness": {"name": "nanobot", "version": _version(binary)},
            "binary": binary,
            "execution_implemented": True,
            "execution_ready": False,
            "execution_requires": "digest-pinned OCI clean room",
            "protocol": "nanobot-direct",
            "prompt_transport": "argv-exact-string",
            "control_proof": {
                "configured": True,
                "runtime": True,
                "provider_wire": False,
            },
            "tools": ["native NanoBot toolset; capture required at execution"],
            "mcp_servers": [],
            "memory": {"mode": "fresh workspace", "scope": "trial"},
            "permissions": "container boundary with workspace restriction",
            "subagents": {"policy": control.auxiliary_model_policy},
            "limitations": [
                "historical temporal proxy rather than a same-date Harness release",
                "Python transitive dependencies are image-local but not yet cross-machine locked",
            ],
        }

    def invocation(
        self,
        contender: ContenderSpec,
        control: ControlProfile,
        worktree: Path,
        task_path: Path,
    ) -> dict[str, Any]:
        provider = control.provider_id.replace("-", "_")
        model = (
            control.requested_id
            if "/" in control.requested_id
            else f"{control.provider_id}/{control.requested_id}"
        )
        return {
            "argv": [
                "env",
                f"NANOBOT_AGENTS__DEFAULTS__MODEL={model}",
                f"NANOBOT_AGENTS__DEFAULTS__PROVIDER={provider}",
                f"NANOBOT_AGENTS__DEFAULTS__REASONING_EFFORT={control.wire_parameter}",
                f"NANOBOT_AGENTS__DEFAULTS__WORKSPACE={worktree}",
                "NANOBOT_TOOLS__RESTRICT_TO_WORKSPACE=true",
                "nanobot",
                "agent",
                "--workspace",
                str(worktree),
                "--session",
                "highlander:direct",
                "--no-markdown",
                "--logs",
                "--message",
            ],
            "cwd": str(worktree),
            "protocol": "nanobot-direct",
            "prompt_transport": "exact Task string appended after --message",
            "task_sha_source": str(task_path),
            "inherited_environment_names": [],
            "credential_values_recorded": False,
        }


class AtomicHarnessAdapter(HarnessAdapter):
    name = "atomic"

    def probe(
        self, contender: ContenderSpec, control: ControlProfile
    ) -> dict[str, Any]:
        binary = shutil.which("atomic")
        return {
            "harness": {"name": "atomic", "version": _version(binary)},
            "binary": binary,
            "execution_implemented": True,
            "execution_ready": False,
            "execution_requires": "digest-pinned OCI clean room",
            "protocol": "atomic-jsonl",
            "prompt_transport": "argv-exact-string",
            "control_proof": {
                "configured": True,
                "runtime": True,
                "provider_wire": False,
            },
            "tools": ["native Atomic clean-core toolset; capture required at execution"],
            "mcp_servers": [],
            "memory": {"mode": "ephemeral no-session", "scope": "trial"},
            "permissions": "container boundary; Atomic has no built-in sandbox",
            "subagents": {"policy": control.auxiliary_model_policy},
            "limitations": [
                "personal resources and project-local executable configuration are disabled",
                "subscription provider/wire proof depends on native JSONL evidence",
            ],
        }

    def invocation(
        self,
        contender: ContenderSpec,
        control: ControlProfile,
        worktree: Path,
        task_path: Path,
    ) -> dict[str, Any]:
        return {
            "argv": [
                "atomic",
                "--mode",
                "json",
                "--print",
                "--provider",
                control.provider_id,
                "--model",
                control.requested_id,
                "--thinking",
                control.reasoning_requested,
                "--no-session",
                "--no-skills",
                "--no-prompt-templates",
                "--no-themes",
                "--no-context-files",
                "--no-approve",
                "--offline",
                "--",
            ],
            "cwd": str(worktree),
            "protocol": "atomic-jsonl",
            "prompt_transport": "exact Task string appended after --",
            "task_sha_source": str(task_path),
            "inherited_environment_names": [],
            "credential_values_recorded": False,
        }


ADAPTERS: dict[str, HarnessAdapter] = {
    adapter.name: adapter
    for adapter in (
        FakeHarnessAdapter(),
        OmpHarnessAdapter(),
        OpenCodeHarnessAdapter(),
        CodexHarnessAdapter(),
        HermesHarnessAdapter(),
        NanoBotHarnessAdapter(),
        AtomicHarnessAdapter(),
    )
}


def adapter_for(name: str) -> HarnessAdapter:
    try:
        return ADAPTERS[name]
    except KeyError as exc:
        raise HighlanderError(f"Unknown Harness Adapter: {name}") from exc


def _version(binary: str | None) -> str | None:
    if not binary:
        return None
    for flag in ("--version", "version"):
        try:
            result = subprocess.run(
                [binary, flag], capture_output=True, text=True, timeout=5, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        text = (result.stdout or result.stderr).strip().splitlines()
        if text:
            return text[0][:200]
    return "installed-version-unavailable"

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
            "execution_implemented": False,
            "execution_ready": False,
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
                "native RPC execution and post-run control parser are not implemented",
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
            "--mode",
            "rpc",
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
            "protocol": "omp-rpc",
            "prompt_transport": "RPC prompt message after start gate",
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
            "execution_implemented": False,
            "execution_ready": False,
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
                "native JSON execution and post-run control parser are not implemented",
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


ADAPTERS: dict[str, HarnessAdapter] = {
    adapter.name: adapter
    for adapter in (FakeHarnessAdapter(), OmpHarnessAdapter(), OpenCodeHarnessAdapter())
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

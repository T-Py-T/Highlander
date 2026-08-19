"""Disposable OCI Arena implementation for raw Harness Trials."""

from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .model import CleanRoomSpec, HighlanderError


BARE_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CleanRoom:
    """Hide image proof, clone isolation, container execution, and cleanup."""

    def __init__(self, config: CleanRoomSpec | dict[str, Any]):
        self.config = asdict(config) if isinstance(config, CleanRoomSpec) else dict(config)
        self.runtime = self.config["runtime"]

    def probe(self) -> dict[str, Any]:
        binary = shutil.which(self.runtime)
        if not binary:
            return {
                "adapter": "oci",
                "runtime": self.runtime,
                "available": False,
                "reason": f"{self.runtime} is not installed",
            }
        version = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, check=False
        )
        info = subprocess.run(
            [binary, "info"], capture_output=True, text=True, check=False
        )
        return {
            "adapter": "oci",
            "runtime": self.runtime,
            "binary": binary,
            "version": (version.stdout or version.stderr).strip().splitlines()[0]
            if (version.stdout or version.stderr).strip()
            else None,
            "available": version.returncode == 0 and info.returncode == 0,
            "daemon_reachable": info.returncode == 0,
            "reason": None
            if info.returncode == 0
            else (info.stderr or info.stdout).strip()[:500],
        }

    def inspect_image(
        self, reference: str, expected_harness: str
    ) -> dict[str, Any]:
        result = subprocess.run(
            [self.runtime, "image", "inspect", reference],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise HighlanderError(
                f"pinned image is unavailable to {self.runtime}: {reference}: "
                f"{(result.stderr or result.stdout).strip()}"
            )
        try:
            payload = json.loads(result.stdout)
            inspected = payload[0]
            image_id = inspected["Id"]
            if isinstance(image_id, str) and BARE_SHA256.fullmatch(image_id):
                image_id = f"sha256:{image_id}"
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise HighlanderError(
                f"{self.runtime} returned invalid image inspection for {reference}"
            ) from exc
        repo_digests = inspected.get("RepoDigests") or []
        if reference.startswith("sha256:"):
            pinned = image_id == reference
        else:
            pinned = reference in repo_digests
        if not pinned:
            raise HighlanderError(
                f"image inspection did not prove requested digest {reference}"
            )
        labels = (inspected.get("Config") or {}).get("Labels") or {}
        if labels.get("io.highlander.harness") != expected_harness:
            raise HighlanderError(
                f"image {reference} is labeled for {labels.get('io.highlander.harness')!r}, "
                f"not {expected_harness!r}"
            )
        image_profile = labels.get("io.highlander.profile")
        if image_profile != self.config["profile"]:
            raise HighlanderError(
                f"image {reference} profile {image_profile!r} does not match "
                f"Match profile {self.config['profile']!r}"
            )
        return {
            "reference": reference,
            "image_id": image_id,
            "repo_digests": repo_digests,
            "architecture": inspected.get("Architecture"),
            "os": inspected.get("Os"),
            "labels": labels,
            "digest_verified": True,
        }

    def plan_trial(
        self,
        *,
        match_id: str,
        contender_id: str,
        adapter: str,
        image: str,
        seed_profile: str | None,
        authentication_required: bool,
    ) -> dict[str, Any]:
        inspected = self.inspect_image(image, adapter)
        seed = self.inspect_seed(adapter, seed_profile, authentication_required)
        return {
            "adapter": "oci",
            "runtime": self.runtime,
            "profile": self.config["profile"],
            "image_reference": image,
            **inspected,
            "seed_profile": seed_profile,
            "seed": seed,
            "container_name": _container_name(match_id, contender_id),
            "network": self.config["network"],
            "resources": {
                "cpus": self.config["cpus"],
                "memory_mb": self.config["memory_mb"],
                "pids_limit": self.config["pids_limit"],
                "tmpfs_mb": self.config["tmpfs_mb"],
            },
            "root_filesystem": "read-only",
            "capabilities": "all-dropped",
            "no_new_privileges": True,
            "host_home_mounted": False,
            "publication_credentials_available": False,
        }

    def inspect_seed(
        self, adapter: str, profile: str | None, required: bool
    ) -> dict[str, Any]:
        if not profile:
            return {
                "profile": None,
                "required": required,
                "available": not required,
                "imported_file": None,
            }
        root_value = os.environ.get(
            "HIGHLANDER_SEED_ROOT",
            str(Path.home() / ".config" / "highlander" / "seeds"),
        )
        root = Path(root_value).expanduser().resolve()
        seed = (root / profile).resolve()
        if root not in seed.parents:
            return {
                "profile": profile,
                "required": required,
                "available": False,
                "imported_file": None,
                "reason": "seed profile escaped configured root",
            }
        if adapter == "omp":
            candidates = [seed / "agent.db"]
        elif adapter == "opencode":
            candidates = [seed / "opencode" / "auth.json", seed / "auth.json"]
        elif adapter == "nanobot":
            candidates = [seed / "oauth.json"]
        elif adapter in {"codex", "hermes"}:
            candidates = [seed / "auth.json"]
        else:
            candidates = []
        imported = next((path for path in candidates if path.is_file()), None)
        return {
            "profile": profile,
            "required": required,
            "available": imported is not None,
            "imported_file": imported.name if imported else None,
        }

    @staticmethod
    def prepare_clone(
        source: Path, base_sha: str, workspace: Path, trial_id: str
    ) -> None:
        if workspace.exists():
            raise HighlanderError(f"clean-room workspace already exists: {workspace}")
        workspace.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--no-local",
                "--no-checkout",
                str(source),
                str(workspace),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise HighlanderError(
                f"could not create independent clone for {trial_id}: {result.stderr.strip()}"
            )
        checkout = subprocess.run(
            ["git", "-C", str(workspace), "checkout", "--quiet", "--detach", base_sha],
            capture_output=True,
            text=True,
            check=False,
        )
        if checkout.returncode != 0:
            raise HighlanderError(
                f"could not freeze {trial_id} at {base_sha}: {checkout.stderr.strip()}"
            )
        subprocess.run(
            ["git", "-C", str(workspace), "remote", "remove", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        marker = {
            "owner": "highlander-clean-room-v1",
            "trial_id": trial_id,
            "base_sha": base_sha,
            "publication_remote_removed": True,
        }
        (workspace / ".git" / "highlander-clean-room.json").write_text(
            json.dumps(marker, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def execute_harness(
        self,
        plan: dict[str, Any],
        task_text: str,
        output_path: Path,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        clean = plan["clean_room"]
        command = list(plan["invocation"]["argv"])
        command.append(task_text)
        seed = self._seed_path(clean.get("seed_profile"))
        argv = self._container_argv(
            name=clean["container_name"],
            image=clean["image_reference"],
            workspace=Path(plan["worktree"]),
            command=command,
            adapter=plan["adapter"],
            seed=seed,
            read_only_workspace=False,
        )
        started_ns = time.time_ns()
        returncode, timed_out = _capture_process(argv, output_path, timeout_seconds)
        reconciliation = self.reconcile(clean)
        redacted_argv = list(argv)
        redacted_argv[-1] = "<TASK_BYTES_UTF8>"
        return {
            "argv_redacted": redacted_argv,
            "returncode": returncode,
            "timed_out": timed_out,
            "started_ns": started_ns,
            "completed_ns": time.time_ns(),
            **reconciliation,
        }

    def evaluate(
        self,
        plan: dict[str, Any],
        commands: list[dict[str, Any]],
        validation_dir: Path,
    ) -> dict[str, Any]:
        validation_dir.mkdir(parents=True, exist_ok=True)
        evaluation = plan.get("evaluation") or {}
        source_workspace = Path(plan["worktree"])
        evaluation_workspace = validation_dir.parent / ".evaluation-workspace"
        if evaluation_workspace.exists():
            raise HighlanderError(
                f"evaluation workspace already exists: {evaluation_workspace}"
            )
        shutil.copytree(source_workspace, evaluation_workspace, symlinks=True)
        results: list[dict[str, Any]] = []
        observed_hash = None
        observed_files = 0
        try:
            overlay_path = evaluation.get("overlay")
            if overlay_path:
                overlay = Path(overlay_path)
                observed_hash, observed_files = _sha256_tree(overlay)
                if observed_hash != evaluation.get("overlay_sha256"):
                    raise HighlanderError("evaluation overlay changed after plan review")
                for source in sorted(overlay.rglob("*")):
                    relative = source.relative_to(overlay)
                    destination = evaluation_workspace / relative
                    if source.is_symlink():
                        raise HighlanderError(
                            "evaluation overlays cannot contain symbolic links"
                        )
                    if source.is_dir():
                        destination.mkdir(parents=True, exist_ok=True)
                    elif source.is_file():
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, destination)
            for command in commands:
                name = _container_name(
                    plan["match_id"], f"eval-{plan['contender_id']}-{command['id']}"
                )
                argv = self._container_argv(
                    name=name,
                    image=self.config["evaluator_image"],
                    workspace=evaluation_workspace,
                    command=list(command["argv"]),
                    adapter="evaluator",
                    seed=None,
                    read_only_workspace=True,
                )
                output_path = validation_dir / f"{command['id']}.log"
                started = time.time_ns()
                returncode, timed_out = _capture_process(
                    argv, output_path, command["timeout_seconds"]
                )
                cleanup = self.reconcile(
                    {"container_name": name, "runtime": self.runtime}
                )
                results.append(
                    {
                        "id": command["id"],
                        "argv": command["argv"],
                        "timeout_seconds": command["timeout_seconds"],
                        "returncode": returncode,
                        "timed_out": timed_out,
                        "duration_ms": round((time.time_ns() - started) / 1_000_000, 3),
                        "output": output_path.name,
                        **cleanup,
                    }
                )
        finally:
            shutil.rmtree(evaluation_workspace)
        passed = all(
            item["returncode"] == 0
            and not item["timed_out"]
            and item["container_reconciled"]
            for item in results
        )
        return {
            "status": "passed" if passed else "failed",
            "commands": results,
            "overlay_sha256": observed_hash,
            "overlay_files": observed_files,
            "evaluation_workspace_removed": not evaluation_workspace.exists(),
        }

    def reconcile(self, clean: dict[str, Any]) -> dict[str, Any]:
        name = clean["container_name"]
        inspect = subprocess.run(
            [self.runtime, "inspect", name],
            capture_output=True,
            text=True,
            check=False,
        )
        if inspect.returncode != 0:
            return {"container_reconciled": True, "container_already_absent": True}
        try:
            payload = json.loads(inspect.stdout)[0]
            labels = ((payload.get("Config") or {}).get("Labels") or {})
        except (json.JSONDecodeError, IndexError, TypeError) as exc:
            raise HighlanderError(
                f"cannot verify ownership of retained container {name}"
            ) from exc
        if labels.get("io.highlander.owner") != "highlander-clean-room-v1":
            raise HighlanderError(
                f"refusing to remove container without Highlander ownership label: {name}"
            )
        removed = subprocess.run(
            [self.runtime, "rm", "--force", name],
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "container_reconciled": removed.returncode == 0,
            "container_already_absent": False,
        }

    @staticmethod
    def remove_workspace(workspace: Path, run_dir: Path, retain: bool) -> dict[str, Any]:
        resolved = workspace.resolve()
        workspace_root = (run_dir / "workspaces").resolve()
        if retain:
            return {
                "workspace": str(resolved),
                "workspace_removed": False,
                "workspace_policy": "retained_by_match_configuration",
            }
        if resolved == workspace_root or workspace_root not in resolved.parents:
            raise HighlanderError(
                f"refusing to remove workspace outside Match ownership: {resolved}"
            )
        marker = resolved / ".git" / "highlander-clean-room.json"
        if not marker.is_file():
            raise HighlanderError(
                f"refusing to remove workspace without ownership marker: {resolved}"
            )
        shutil.rmtree(resolved)
        return {
            "workspace": str(resolved),
            "workspace_removed": not resolved.exists(),
            "workspace_policy": "destroyed_after_raw_patch_capture",
        }

    def _seed_path(self, profile: str | None) -> Path | None:
        if not profile:
            return None
        root_value = os.environ.get("HIGHLANDER_SEED_ROOT")
        if not root_value:
            raise HighlanderError(
                f"seed profile {profile!r} requires HIGHLANDER_SEED_ROOT"
            )
        root = Path(root_value).expanduser().resolve()
        seed = (root / profile).resolve()
        if root not in seed.parents or not seed.is_dir():
            raise HighlanderError(f"clean seed profile is unavailable: {profile}")
        return seed

    def _container_argv(
        self,
        *,
        name: str,
        image: str,
        workspace: Path,
        command: list[str],
        adapter: str,
        seed: Path | None,
        read_only_workspace: bool,
    ) -> list[str]:
        uid = os.getuid() if hasattr(os, "getuid") else 1000
        gid = os.getgid() if hasattr(os, "getgid") else 1000
        workspace_value = str(workspace.resolve())
        if "," in workspace_value:
            raise HighlanderError("clean-room workspace paths cannot contain commas")
        resources = self.config
        argv = [
            self.runtime,
            "run",
            "--rm",
            "--name",
            name,
            "--label",
            "io.highlander.owner=highlander-clean-room-v1",
            "--label",
            f"io.highlander.adapter={adapter}",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit",
            str(resources["pids_limit"]),
            "--cpus",
            str(resources["cpus"]),
            "--memory",
            f"{resources['memory_mb']}m",
            "--network",
            resources["network"],
            "--user",
            f"{uid}:{gid}",
            "--tmpfs",
            f"/tmp:rw,nosuid,nodev,size={resources['tmpfs_mb']}m,uid={uid},gid={gid},mode=1777",
            "--tmpfs",
            f"/home/highlander:rw,nosuid,nodev,size={resources['tmpfs_mb']}m,uid={uid},gid={gid},mode=0700",
            "--mount",
            f"type=bind,src={workspace_value},dst=/workspace,{'readonly' if read_only_workspace else 'rw'}",
            "--workdir",
            "/workspace",
            "--env",
            "HOME=/home/highlander",
            "--env",
            f"HIGHLANDER_HARNESS={adapter}",
        ]
        if seed:
            seed_value = str(seed)
            if "," in seed_value:
                raise HighlanderError("clean seed paths cannot contain commas")
            argv.extend(
                [
                    "--mount",
                    f"type=bind,src={seed_value},dst=/run/highlander/seed,readonly",
                ]
            )
        argv.extend([image, *command])
        return argv


def extract_control_proof(
    output_path: Path, expected: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    records: list[Any] = []
    text_parts: list[str] = []
    for line in output_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            text_parts.append(line)
            continue
        records.append(value)
        _collect_text(value, text_parts)
    observed = {
        "model": _find_value(records, {"model", "modelID", "model_id"}),
        "provider": _find_value(records, {"provider", "providerID", "provider_id"}),
        "reasoning": _find_value(records, {"reasoning", "variant", "effort"}),
        "upstream_id": _find_value(records, {"upstream_id", "upstreamID"}),
        "endpoint_or_deployment": _find_value(
            records, {"endpoint_or_deployment", "endpoint", "deployment"}
        ),
        "region": _find_value(records, {"region"}),
    }
    runtime_verified = all(
        observed[field] == expected[field] for field in ("model", "provider", "reasoning")
    )
    provider_verified = runtime_verified and all(
        observed[field] == expected[field]
        for field in ("upstream_id", "endpoint_or_deployment", "region")
    )
    proof = {
        "observed": observed,
        "records_examined": len(records),
        "runtime_verified": runtime_verified,
        "provider_verified": provider_verified,
    }
    return proof, "\n".join(part for part in text_parts if part).strip()


def _capture_process(
    argv: list[str], output_path: Path, timeout_seconds: int
) -> tuple[int, bool]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    timed_out = False
    try:
        output, _ = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        output, _ = process.communicate()
    output_path.write_bytes(output)
    if output:
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.flush()
    return (124 if timed_out else process.returncode), timed_out


def _container_name(match_id: str, suffix: str) -> str:
    value = f"highlander-{match_id}-{suffix}-a1".lower()
    return value[:120]


def _find_value(value: Any, names: set[str]) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in names and isinstance(child, (str, int, float, bool)):
                return child
        for child in value.values():
            found = _find_value(child, names)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_value(child, names)
            if found is not None:
                return found
    return None


def _collect_text(value: Any, output: list[str]) -> None:
    if isinstance(value, dict):
        for key in ("text", "message", "content"):
            child = value.get(key)
            if isinstance(child, str):
                output.append(child)
        for child in value.values():
            if isinstance(child, (dict, list)):
                _collect_text(child, output)
    elif isinstance(value, list):
        for child in value:
            _collect_text(child, output)


def _sha256_tree(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    files = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
        files += 1
    return digest.hexdigest(), files

#!/usr/bin/env python3
"""Build, seed, inspect, and generate disposable Highlander Matches."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / ".highlander" / "images.lock.json"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
BARE_SHA256 = re.compile(r"^[0-9a-f]{64}$")
TAGS = {
    "evaluator": "highlander/evaluator:go1.27.1-bookworm-v1",
    "omp": "highlander/omp:18.1.19-clean-core",
    "opencode": "highlander/opencode:1.18.30-clean-core",
    "nanobot": "highlander/nanobot:0.3.0-clean-core",
    "codex": "highlander/codex:0.154.0-clean-core",
    "hermes": "highlander/hermes:0.21.2-clean-core",
    "atomic": "highlander/atomic:0.9.18-clean-core",
}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="clean-room.py")
    value.add_argument(
        "--runtime", choices=("docker", "podman"), default="docker"
    )
    value.add_argument("--lock", default=str(DEFAULT_LOCK))
    commands = value.add_subparsers(dest="command", required=True)

    commands.add_parser("build", help="build pinned local clean-core images")

    seed = commands.add_parser("seed", help="create an authentication-only seed")
    seed.add_argument(
        "harness", choices=("omp", "opencode", "nanobot", "codex", "hermes", "atomic")
    )
    seed.add_argument("profile")
    seed.add_argument(
        "--seed-root",
        default=os.environ.get(
            "HIGHLANDER_SEED_ROOT",
            str(Path.home() / ".config" / "highlander" / "seeds"),
        ),
    )

    commands.add_parser("doctor", help="verify runtime, images, and image labels")

    match = commands.add_parser("new-match", help="write a digest-pinned Match JSON")
    match.add_argument("--match-id", required=True)
    match.add_argument("--arena", required=True)
    match.add_argument("--base-ref", required=True)
    match.add_argument("--task", required=True)
    match.add_argument("--model", required=True)
    match.add_argument("--upstream-model")
    match.add_argument("--provider", required=True)
    match.add_argument("--endpoint", required=True)
    match.add_argument("--region", default="unknown")
    match.add_argument("--reasoning", required=True)
    match.add_argument("--wire-reasoning")
    match.add_argument("--auth-route", default="subscription")
    match.add_argument("--omp-seed", default="omp-subscription")
    match.add_argument("--opencode-seed", default="opencode-subscription")
    match.add_argument("--codex-seed", default="codex-subscription")
    match.add_argument("--hermes-seed", default="hermes-subscription")
    match.add_argument("--nanobot-seed", default="nanobot-subscription")
    match.add_argument("--atomic-seed", default="atomic-subscription")
    match.add_argument("--session", choices=("headless", "tmux"), default="tmux")
    match.add_argument("--wall-time", type=int, default=1800)
    match.add_argument("--output-root")
    match.add_argument(
        "--evaluation-overlay",
        default=str(ROOT / "evaluators" / "T002-linewatch-alarm-id-whitespace"),
    )
    match.add_argument("--output", required=True)
    return value


def run_checked(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    result = subprocess.run(argv, check=False, **kwargs)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {shlex.join(argv)}")
    return result


def strip_container_file_metadata(path: Path) -> None:
    """Remove container-runtime ownership overrides from a host-exported file."""

    if not path.is_file():
        return
    names = ("user.containers.override_stat", "security.selinux")
    if hasattr(os, "listxattr"):
        present = set(os.listxattr(path))
        for name in names:
            if name in present:
                os.removexattr(path, name)
        return
    if sys.platform == "darwin":
        for name in names:
            present = subprocess.run(
                ["/usr/bin/xattr", "-p", name, str(path)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if present.returncode == 0:
                run_checked(
                    ["/usr/bin/xattr", "-d", name, str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )


def runtime_ready(runtime: str) -> None:
    run_checked([runtime, "--version"], stdout=subprocess.DEVNULL)
    run_checked(
        [runtime, "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def inspect_image(runtime: str, reference: str) -> dict[str, Any]:
    result = run_checked(
        [runtime, "image", "inspect", reference],
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)[0]
    image_id = payload["Id"]
    if isinstance(image_id, str) and BARE_SHA256.fullmatch(image_id):
        image_id = f"sha256:{image_id}"
    return {
        "tag": reference,
        "image_id": image_id,
        "architecture": payload.get("Architecture"),
        "os": payload.get("Os"),
        "labels": (payload.get("Config") or {}).get("Labels") or {},
    }


def build(runtime: str, lock_path: Path) -> None:
    runtime_ready(runtime)
    machine = platform.machine().lower()
    target_arch = "arm64" if machine in {"arm64", "aarch64"} else "amd64"
    builds = [
        (
            "evaluator",
            [
                runtime,
                "build",
                "--build-arg",
                f"TARGETARCH={target_arch}",
                "--tag",
                TAGS["evaluator"],
                "--file",
                str(ROOT / "containers" / "base" / "Dockerfile"),
                str(ROOT),
            ],
        ),
        (
            "omp",
            [
                runtime,
                "build",
                "--build-arg",
                f"TARGETARCH={target_arch}",
                "--build-arg",
                f"BASE_IMAGE={TAGS['evaluator']}",
                "--tag",
                TAGS["omp"],
                "--file",
                str(ROOT / "containers" / "omp" / "Dockerfile"),
                str(ROOT),
            ],
        ),
        (
            "opencode",
            [
                runtime,
                "build",
                "--build-arg",
                f"TARGETARCH={target_arch}",
                "--build-arg",
                f"BASE_IMAGE={TAGS['evaluator']}",
                "--tag",
                TAGS["opencode"],
                "--file",
                str(ROOT / "containers" / "opencode" / "Dockerfile"),
                str(ROOT),
            ],
        ),
        (
            "nanobot",
            [
                runtime,
                "build",
                "--build-arg",
                f"BASE_IMAGE={TAGS['evaluator']}",
                "--tag",
                TAGS["nanobot"],
                "--file",
                str(ROOT / "containers" / "nanobot" / "Dockerfile"),
                str(ROOT),
            ],
        ),
        (
            "codex",
            [
                runtime,
                "build",
                "--build-arg",
                f"TARGETARCH={target_arch}",
                "--build-arg",
                f"BASE_IMAGE={TAGS['evaluator']}",
                "--tag",
                TAGS["codex"],
                "--file",
                str(ROOT / "containers" / "codex" / "Dockerfile"),
                str(ROOT),
            ],
        ),
        (
            "hermes",
            [
                runtime,
                "build",
                "--build-arg",
                f"TARGETARCH={target_arch}",
                "--build-arg",
                f"BASE_IMAGE={TAGS['evaluator']}",
                "--tag",
                TAGS["hermes"],
                "--file",
                str(ROOT / "containers" / "hermes" / "Dockerfile"),
                str(ROOT),
            ],
        ),
        (
            "atomic",
            [
                runtime,
                "build",
                "--build-arg",
                f"TARGETARCH={target_arch}",
                "--build-arg",
                f"BASE_IMAGE={TAGS['evaluator']}",
                "--tag",
                TAGS["atomic"],
                "--file",
                str(ROOT / "containers" / "atomic" / "Dockerfile"),
                str(ROOT),
            ],
        ),
    ]
    for name, argv in builds:
        print(f"Building {name} clean-room image...", flush=True)
        run_checked(argv)
    images = {name: inspect_image(runtime, tag) for name, tag in TAGS.items()}
    lock = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "runtime": runtime,
        "profile": "clean-core",
        "images": images,
        "sources": {
            "omp": {
                "version": "18.1.19",
                "linux_amd64_sha256": "4b5df0c61cc978223bd12f7e8d533554e80bb360a9192491de13da3d53b283ac",
                "linux_arm64_sha256": "b321b6bb2a96068df2f4972f98654c23e451371a275cfbb0a98ef6f5f858f239",
            },
            "opencode": {
                "version": "1.18.30",
                "linux_amd64_sha256": "55007246858165496ff85ba1c2b648f7421e8e2013bf4189a680c9ff8e699d17",
                "linux_arm64_sha256": "4111a55c2a02c0fac314bd51e9a2330280e6d29d2b85b9554fff6d62612566ed",
            },
            "nanobot": {
                "version": "0.3.0",
                "package": "nanobot-ai==0.3.0",
                "role": "current-release",
            },
            "codex": {
                "version": "0.154.0",
                "release_tag": "rust-v0.154.0",
                "linux_amd64_sha256": "d7e18b2597ae8f242f5f31ee9e90deef48dbc9edd634d9868fb6435d08c07f02",
                "linux_arm64_sha256": "583b48df32804213bdcd338c2e5adb06b34340821fa757a726cc0a524fa33c27",
            },
            "hermes": {
                "version": "0.21.2",
                "release_tag": "v2026.9.11",
                "commit": "939e45c91d751fadd94dcd1b873ac3cb44846213",
                "uv_lock_sha256": "69b130365c9077ac9880c167daa64e39afc5611bb563a79a2fb3c612949beae9",
                "uv_version": "0.12.13",
            },
            "atomic": {
                "version": "0.9.18",
                "release_tag": "0.9.18",
                "linux_amd64_sha256": "51ca278acda3fdb674e7e2d2828de0891dc3e70eef8e7cbdb04f45951fcfbfa6",
                "linux_arm64_sha256": "d70e28713e79defb6d0f785ccbab0e8d252f8416e5d3028622f05018d19cfd9a",
            },
        },
    }
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Image lock written to {lock_path}")


def load_lock(lock_path: Path) -> dict[str, Any]:
    if not lock_path.is_file():
        raise RuntimeError(f"image lock not found; run build first: {lock_path}")
    return json.loads(lock_path.read_text(encoding="utf-8"))


def seed(runtime: str, lock: dict[str, Any], harness: str, profile: str, seed_root: Path) -> None:
    if not SAFE_ID.fullmatch(profile):
        raise RuntimeError("seed profile must be a safe 1-64 character identifier")
    destination = (seed_root.expanduser().resolve() / profile).resolve()
    root = seed_root.expanduser().resolve()
    if root not in destination.parents:
        raise RuntimeError("seed profile escaped the configured seed root")
    if destination.exists():
        raise RuntimeError(
            f"seed already exists; choose a new profile instead of mutating it: {destination}"
        )
    destination.mkdir(parents=True, mode=0o700)
    image = lock["images"][harness]["image_id"]
    uid = os.getuid() if hasattr(os, "getuid") else 1000
    gid = os.getgid() if hasattr(os, "getgid") else 1000
    managed_volume = harness == "omp"
    volume_name = f"highlander-seed-{profile}" if managed_volume else None
    if volume_name:
        found = subprocess.run(
            [runtime, "volume", "inspect", volume_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if found.returncode == 0:
            raise RuntimeError(
                f"auth seed volume already exists; inspect or remove it first: {volume_name}"
            )
        run_checked(
            [
                runtime,
                "volume",
                "create",
                "--label",
                "com.highlander.managed=true",
                "--label",
                "com.highlander.purpose=auth-seed",
                volume_name,
            ],
            stdout=subprocess.DEVNULL,
        )
    # OMP stores credentials in SQLite. Docker Desktop and Podman Desktop host
    # binds do not reliably provide the locking semantics SQLite needs, so OMP
    # logs in on a private engine volume as root. Only its checkpointed agent.db
    # is exported afterward. Scored Trial containers remain unprivileged and
    # import that one file read-only.
    seed_uid, seed_gid = (0, 0) if managed_volume else (uid, gid)
    seed_mount = (
        f"type=volume,src={volume_name},dst=/seed-output,rw"
        if volume_name
        else f"type=bind,src={destination},dst=/seed-output,rw"
    )
    argv = [
        runtime,
        "run",
        "--rm",
        "--interactive",
        "--tty",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--network",
        "bridge",
        "--user",
        f"{seed_uid}:{seed_gid}",
        "--tmpfs",
        "/home/highlander:rw,nosuid,nodev,size=512m,mode=1777",
        "--mount",
        seed_mount,
        "--env",
        # The image contains root-owned .config/.local directories under the
        # tmpfs mount point.  Use a fresh child exactly like scored Trials so
        # the unprivileged runtime user can initialize a clean login home.
        "HOME=/home/highlander/runtime",
        "--env",
        "XDG_CACHE_HOME=/home/highlander/runtime/.cache",
        "--env",
        "XDG_CONFIG_HOME=/home/highlander/runtime/.config",
        "--env",
        "XDG_DATA_HOME=/home/highlander/runtime/.local/share",
        "--env",
        "XDG_STATE_HOME=/home/highlander/runtime/.local/state",
        "--env",
        f"HIGHLANDER_HARNESS={harness}",
    ]
    if harness == "omp":
        argv.extend(
            [
                "--env",
                "PI_CODING_AGENT_DIR=/seed-output",
                image,
                "omp",
                "--no-extensions",
                "--no-skills",
                "--no-rules",
                "--no-session",
                "--no-title",
                "--no-prewalk",
            ]
        )
        expected = destination / "agent.db"
    elif harness == "opencode":
        argv.extend(
            [
                "--env",
                "XDG_DATA_HOME=/seed-output",
                image,
                "opencode",
                "auth",
                "login",
            ]
        )
        expected = destination / "opencode" / "auth.json"
    elif harness == "nanobot":
        argv.extend(
            [
                "--env",
                "OAUTH_CLI_KIT_TOKEN_PATH=/seed-output/oauth.json",
                image,
                "nanobot",
                "provider",
                "login",
                "openai-codex",
            ]
        )
        expected = destination / "oauth.json"
    elif harness == "codex":
        argv.extend(
            [
                "--env",
                "CODEX_HOME=/seed-output",
                image,
                "codex",
                "login",
                "--device-auth",
                "--config",
                'cli_auth_credentials_store="file"',
            ]
        )
        expected = destination / "auth.json"
    elif harness == "hermes":
        argv.extend(
            [
                "--env",
                "HERMES_HOME=/seed-output",
                image,
                "hermes",
                "auth",
                "add",
                "openai-codex",
                "--type",
                "oauth",
                "--no-browser",
                "--label",
                "highlander",
            ]
        )
        expected = destination / "auth.json"
    else:
        argv.extend(
            [
                "--env",
                "ATOMIC_CODING_AGENT_DIR=/seed-output",
                image,
                "atomic",
                "--provider",
                "openai-codex",
                "--model",
                "gpt-5.6-luna",
                "--no-session",
                "--no-extensions",
                "--no-skills",
                "--no-prompt-templates",
                "--no-themes",
                "--no-context-files",
                "--no-approve",
                "--offline",
            ]
        )
        expected = destination / "auth.json"
    print(
        "Complete the subscription login inside the disposable container, then exit.",
        flush=True,
    )
    result = subprocess.run(argv, check=False)
    if result.returncode == 0 and volume_name:
        run_checked(
            [
                runtime,
                "run",
                "--rm",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--network",
                "none",
                "--user",
                "0:0",
                "--mount",
                f"type=volume,src={volume_name},dst=/seed-output,rw",
                image,
                "python3",
                "-c",
                (
                    "import sqlite3; "
                    "db=sqlite3.connect('/seed-output/agent.db'); "
                    "db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchall(); "
                    "db.close()"
                ),
            ],
            stdout=subprocess.DEVNULL,
        )
        run_checked(
            [
                runtime,
                "run",
                "--rm",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--network",
                "none",
                "--user",
                "0:0",
                "--mount",
                f"type=volume,src={volume_name},dst=/seed-output,ro",
                "--mount",
                f"type=bind,src={destination},dst=/seed-export,rw",
                image,
                "/bin/sh",
                "-c",
                "cp /seed-output/agent.db /seed-export/agent.db && chmod 600 /seed-export/agent.db",
            ],
            stdout=subprocess.DEVNULL,
        )
        strip_container_file_metadata(expected)
    if result.returncode != 0 or not expected.is_file():
        retained = f" and engine volume {volume_name}" if volume_name else ""
        raise RuntimeError(
            "login seed was not completed; partial state retained for inspection at "
            f"{destination}{retained}"
        )
    os.chmod(destination, 0o700)
    os.chmod(expected, 0o600)
    if volume_name:
        run_checked(
            [runtime, "volume", "rm", volume_name],
            stdout=subprocess.DEVNULL,
        )
    print(f"Clean authentication seed created: {profile} ({expected.name} only is imported into Trials)")


def doctor(runtime: str, lock: dict[str, Any]) -> None:
    runtime_ready(runtime)
    rows = []
    for name, saved in lock["images"].items():
        current = inspect_image(runtime, saved["image_id"])
        rows.append(
            {
                "name": name,
                "image_id": current["image_id"],
                "harness": current["labels"].get("io.highlander.harness"),
                "profile": current["labels"].get("io.highlander.profile"),
                "version": current["labels"].get("io.highlander.version"),
                "matches_lock": current["image_id"] == saved["image_id"],
            }
        )
    print(json.dumps({"runtime": runtime, "ready": all(r["matches_lock"] for r in rows), "images": rows}, indent=2))


def new_match(args: argparse.Namespace, lock: dict[str, Any]) -> None:
    if not SAFE_ID.fullmatch(args.match_id):
        raise RuntimeError("match-id must be a safe 1-64 character identifier")
    arena = Path(args.arena).expanduser().resolve()
    task = Path(args.task).expanduser().resolve()
    evaluation_overlay = Path(args.evaluation_overlay).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root
        else output.parent / "runs"
    )
    if not (arena / ".git").exists():
        raise RuntimeError(f"Arena is not a Git repository: {arena}")
    if not task.is_file():
        raise RuntimeError(f"Task not found: {task}")
    if not evaluation_overlay.is_dir():
        raise RuntimeError(f"Evaluation overlay not found: {evaluation_overlay}")
    seed_options = (
        {
            "omp": {"seed_profile": args.omp_seed},
            "opencode": {"seed_profile": args.opencode_seed},
            "codex": {"seed_profile": args.codex_seed},
            "hermes": {"seed_profile": args.hermes_seed},
            "nanobot": {"seed_profile": args.nanobot_seed},
            "atomic": {"seed_profile": args.atomic_seed},
        }
        if args.auth_route != "none"
        else {
            "omp": {},
            "opencode": {},
            "codex": {},
            "hermes": {},
            "nanobot": {},
            "atomic": {},
        }
    )
    payload = {
        "schema_version": 1,
        "match_id": args.match_id,
        "lane": "controlled_efficacy"
        if args.auth_route == "none"
        else "subscription_realism",
        "arena": {
            "repository": str(arena),
            "base_ref": args.base_ref,
            "clean_room": {
                "runtime": args.runtime,
                "profile": "clean-core",
                "evaluator_image": lock["images"]["evaluator"]["image_id"],
                "network": "bridge",
                "cpus": 2,
                "memory_mb": 4096,
                "pids_limit": 512,
                "tmpfs_mb": 1024,
                "retain_workspaces": False,
            },
        },
        "task": {"path": str(task)},
        "control_profile": {
            "model": {
                "requested_id": args.model,
                "upstream_id": args.upstream_model or args.model,
                "provider_id": args.provider,
                "endpoint_or_deployment": args.endpoint,
                "region": args.region,
                "auth_route": args.auth_route,
            },
            "reasoning": {
                "requested": args.reasoning,
                "wire_parameter": args.wire_reasoning or args.reasoning,
            },
            "fallback_policy": "forbidden",
            "auxiliary_model_policy": "same_model",
            "limits": {
                "wall_time_seconds": args.wall_time,
                "external_model_request_cap": 90,
            },
            "proof_required": ["configured", "runtime"],
        },
        "contenders": [
            {
                "id": "omp-clean",
                "adapter": "omp",
                "options": {
                    "approval_mode": "yolo",
                    "image": lock["images"]["omp"]["image_id"],
                    **seed_options["omp"],
                },
            },
            {
                "id": "opencode-clean",
                "adapter": "opencode",
                "options": {
                    "pure": True,
                    "image": lock["images"]["opencode"]["image_id"],
                    **seed_options["opencode"],
                },
            },
            {
                "id": "codex-clean",
                "adapter": "codex",
                "options": {
                    "image": lock["images"]["codex"]["image_id"],
                    **seed_options["codex"],
                },
            },
            {
                "id": "hermes-clean",
                "adapter": "hermes",
                "options": {
                    "image": lock["images"]["hermes"]["image_id"],
                    **seed_options["hermes"],
                },
            },
            {
                "id": "nanobot-clean",
                "adapter": "nanobot",
                "options": {
                    "image": lock["images"]["nanobot"]["image_id"],
                    **seed_options["nanobot"],
                },
            },
            {
                "id": "atomic-clean",
                "adapter": "atomic",
                "options": {
                    "image": lock["images"]["atomic"]["image_id"],
                    **seed_options["atomic"],
                },
            },
        ],
        "evaluation": {
            "overlay": str(evaluation_overlay),
            "commands": [
                {"id": "test", "argv": ["go", "test", "./..."], "timeout_seconds": 300},
                {"id": "race", "argv": ["go", "test", "-race", "./..."], "timeout_seconds": 600},
                {"id": "vet", "argv": ["go", "vet", "./..."], "timeout_seconds": 300},
            ]
        },
        "session": {"adapter": args.session},
        "output_root": str(output_root),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Digest-pinned Match written to {output}")


def main() -> int:
    args = parser().parse_args()
    lock_path = Path(args.lock).expanduser().resolve()
    try:
        if args.command == "build":
            build(args.runtime, lock_path)
        elif args.command == "seed":
            seed(
                args.runtime,
                load_lock(lock_path),
                args.harness,
                args.profile,
                Path(args.seed_root),
            )
        elif args.command == "doctor":
            doctor(args.runtime, load_lock(lock_path))
        elif args.command == "new-match":
            new_match(args, load_lock(lock_path))
    except (OSError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(f"Clean room: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

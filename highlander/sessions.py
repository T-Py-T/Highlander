"""Session Adapters place Highlander workers without interpreting harnesses."""

from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .model import HighlanderError


@dataclass
class SessionHandle:
    adapter: str
    match_id: str | None = None
    processes: list[subprocess.Popen[bytes]] = field(default_factory=list)
    streams: list[Any] = field(default_factory=list)
    tmux_session: str | None = None
    tmux_owned: bool = False
    pane_ids: list[str] = field(default_factory=list)

    def manifest(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "match_id": self.match_id,
            "process_ids": [process.pid for process in self.processes],
            "tmux_session": self.tmux_session,
            "ownership_marker": self.match_id if self.tmux_owned else None,
            "pane_ids": self.pane_ids,
            "credential_values_recorded": False,
        }


class HeadlessSessionAdapter:
    name = "headless"

    def probe(self) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "available": True,
            "visible": False,
            "structured_completion": "worker outcome files",
        }

    def open(self, workers: list[dict[str, Any]], session_name: str) -> SessionHandle:
        handle = SessionHandle(adapter=self.name, match_id=session_name)
        try:
            for worker in workers:
                stdout_path = Path(worker["terminal_log"])
                stdout_path.parent.mkdir(parents=True, exist_ok=True)
                stream = stdout_path.open("ab")
                handle.streams.append(stream)
                process = subprocess.Popen(
                    worker["argv"],
                    cwd=worker["cwd"],
                    env=worker["environment"],
                    stdin=subprocess.DEVNULL,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                handle.processes.append(process)
        except BaseException:
            self.close(handle)
            raise
        return handle

    def close(self, handle: SessionHandle, grace_seconds: float = 2.0) -> dict[str, Any]:
        forced: list[int] = []
        unreconciled: list[int] = []
        exit_codes: dict[str, int | None] = {}
        for process in handle.processes:
            try:
                process.wait(timeout=grace_seconds)
            except subprocess.TimeoutExpired:
                forced.append(process.pid)
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=grace_seconds)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=grace_seconds)
            reconciled = _terminate_process_group(process.pid, grace_seconds)
            if not reconciled:
                unreconciled.append(process.pid)
            exit_codes[str(process.pid)] = process.returncode
        for stream in handle.streams:
            stream.close()
        return {
            "session_closed": not unreconciled,
            "forced_process_ids": forced,
            "unreconciled_process_ids": unreconciled,
            "exit_codes": exit_codes,
        }

    def failure_before_ready(self, handle: SessionHandle) -> str | None:
        for process in handle.processes:
            if process.poll() is not None:
                return f"worker process {process.pid} exited with {process.returncode}"
        return None


class TmuxSessionAdapter:
    name = "tmux"

    def probe(self) -> dict[str, Any]:
        binary = shutil.which("tmux")
        version = None
        if binary:
            result = subprocess.run(
                [binary, "-V"], capture_output=True, text=True, check=False
            )
            version = result.stdout.strip() or result.stderr.strip()
        return {
            "adapter": self.name,
            "available": bool(binary),
            "binary": binary,
            "version": version,
            "visible": True,
            "structured_completion": "worker outcome files",
        }

    def open(self, workers: list[dict[str, Any]], session_name: str) -> SessionHandle:
        binary = shutil.which("tmux")
        if not binary:
            raise HighlanderError("tmux is not installed")
        if not workers:
            raise HighlanderError("cannot open an empty tmux Match")
        safe_name = f"highlander-{session_name}"[:80]
        if subprocess.run(
            [binary, "has-session", "-t", safe_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0:
            raise HighlanderError(f"tmux session already exists: {safe_name}")

        handle = SessionHandle(
            adapter=self.name, match_id=session_name, tmux_session=safe_name
        )
        env_binary = shutil.which("env")
        if not env_binary:
            raise HighlanderError("env is required for isolated tmux workers")
        try:
            for index, worker in enumerate(workers):
                environment = [
                    f"{name}={value}"
                    for name, value in sorted(worker["environment"].items())
                ]
                command = shlex.join(
                    [env_binary, "-i", *environment, *worker["argv"]]
                )
                if index == 0:
                    argv = [
                        binary,
                        "new-session",
                        "-d",
                        "-s",
                        safe_name,
                        "-n",
                        "contenders",
                        "-c",
                        worker["cwd"],
                        "-P",
                        "-F",
                        "#{pane_id}",
                        command,
                    ]
                else:
                    argv = [
                        binary,
                        "split-window",
                        "-d",
                        "-t",
                        f"{safe_name}:0",
                        "-c",
                        worker["cwd"],
                        "-P",
                        "-F",
                        "#{pane_id}",
                        command,
                    ]
                result = subprocess.run(
                    argv, capture_output=True, text=True, check=False
                )
                if result.returncode != 0:
                    raise HighlanderError(
                        f"tmux could not place worker {index + 1}: {result.stderr.strip()}"
                    )
                if index == 0:
                    # A successful new-session proves this process created the target.
                    # Record ownership before any later operation can fail.
                    handle.tmux_owned = True
                    marker = subprocess.run(
                        [
                            binary,
                            "set-option",
                            "-t",
                            safe_name,
                            "@highlander_match_id",
                            session_name,
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if marker.returncode != 0:
                        raise HighlanderError(
                            f"tmux ownership marker failed: {marker.stderr.strip()}"
                        )
                pane_id = result.stdout.strip()
                handle.pane_ids.append(pane_id)
                terminal_log = Path(worker["terminal_log"])
                terminal_log.parent.mkdir(parents=True, exist_ok=True)
                pipe_command = f"cat >> {shlex.quote(str(terminal_log))}"
                pipe = subprocess.run(
                    [binary, "pipe-pane", "-o", "-t", pane_id, pipe_command],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if pipe.returncode != 0:
                    raise HighlanderError(
                        f"tmux could not capture pane {pane_id}: {pipe.stderr.strip()}"
                    )
            subprocess.run(
                [binary, "select-layout", "-t", f"{safe_name}:0", "tiled"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except BaseException:
            self.close(handle)
            raise
        return handle

    def close(self, handle: SessionHandle, grace_seconds: float = 2.0) -> dict[str, Any]:
        binary = shutil.which("tmux")
        if not binary or not handle.tmux_session:
            return {"session_closed": True, "already_absent": True}
        exists = subprocess.run(
            [binary, "has-session", "-t", handle.tmux_session],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
        if exists and not handle.tmux_owned:
            return {
                "session_closed": False,
                "already_absent": False,
                "ownership_verified": False,
            }
        if exists:
            result = subprocess.run(
                [binary, "kill-session", "-t", handle.tmux_session],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return {
                "session_closed": result.returncode == 0,
                "already_absent": False,
                "ownership_verified": True,
            }
        return {"session_closed": True, "already_absent": True}

    def failure_before_ready(self, handle: SessionHandle) -> str | None:
        binary = shutil.which("tmux")
        if not binary or not handle.tmux_session:
            return "tmux session identity is unavailable"
        result = subprocess.run(
            [binary, "has-session", "-t", handle.tmux_session],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            return f"tmux session {handle.tmux_session} exited before release"
        return None


SESSION_ADAPTERS = {
    "headless": HeadlessSessionAdapter(),
    "tmux": TmuxSessionAdapter(),
}


def session_adapter_for(name: str):
    try:
        return SESSION_ADAPTERS[name]
    except KeyError as exc:
        raise HighlanderError(f"Unknown Session Adapter: {name}") from exc


def _terminate_process_group(process_group_id: int, grace_seconds: float) -> bool:
    """Terminate descendants even when their direct Highlander worker exited."""

    if os.name != "posix":
        return False
    if not _process_group_exists(process_group_id):
        return True
    try:
        os.killpg(process_group_id, signal.SIGTERM)
    except ProcessLookupError:
        return True
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if not _process_group_exists(process_group_id):
            return True
        time.sleep(0.05)
    try:
        os.killpg(process_group_id, signal.SIGKILL)
    except ProcessLookupError:
        return True
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if not _process_group_exists(process_group_id):
            return True
        time.sleep(0.05)
    return not _process_group_exists(process_group_id)


def _process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True

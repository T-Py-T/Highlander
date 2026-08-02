"""Session Adapters place Highlander workers without interpreting harnesses."""

from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .model import HighlanderError


@dataclass
class SessionHandle:
    adapter: str
    processes: list[subprocess.Popen[bytes]] = field(default_factory=list)
    streams: list[Any] = field(default_factory=list)
    tmux_session: str | None = None
    pane_ids: list[str] = field(default_factory=list)

    def manifest(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "process_ids": [process.pid for process in self.processes],
            "tmux_session": self.tmux_session,
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
        handle = SessionHandle(adapter=self.name)
        for worker in workers:
            stdout_path = Path(worker["terminal_log"])
            stdout_path.parent.mkdir(parents=True, exist_ok=True)
            stream = stdout_path.open("ab")
            process = subprocess.Popen(
                worker["argv"],
                cwd=worker["cwd"],
                stdin=subprocess.DEVNULL,
                stdout=stream,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            handle.streams.append(stream)
            handle.processes.append(process)
        return handle

    def close(self, handle: SessionHandle, grace_seconds: float = 2.0) -> dict[str, Any]:
        forced: list[int] = []
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
            exit_codes[str(process.pid)] = process.returncode
        for stream in handle.streams:
            stream.close()
        return {
            "session_closed": True,
            "forced_process_ids": forced,
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

        handle = SessionHandle(adapter=self.name, tmux_session=safe_name)
        for index, worker in enumerate(workers):
            command = shlex.join(worker["argv"])
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
            result = subprocess.run(argv, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                self.close(handle)
                raise HighlanderError(
                    f"tmux could not place worker {index + 1}: {result.stderr.strip()}"
                )
            pane_id = result.stdout.strip()
            handle.pane_ids.append(pane_id)
            terminal_log = Path(worker["terminal_log"])
            terminal_log.parent.mkdir(parents=True, exist_ok=True)
            pipe_command = f"cat >> {shlex.quote(str(terminal_log))}"
            subprocess.run(
                [binary, "pipe-pane", "-o", "-t", pane_id, pipe_command],
                capture_output=True,
                text=True,
                check=False,
            )
        subprocess.run(
            [binary, "select-layout", "-t", f"{safe_name}:0", "tiled"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
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

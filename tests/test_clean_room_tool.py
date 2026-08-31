import importlib.util
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "clean-room.py"
SPEC = importlib.util.spec_from_file_location("highlander_clean_room_tool", TOOL_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {TOOL_PATH}")
CLEAN_ROOM_TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLEAN_ROOM_TOOL)


class CleanRoomSeedToolTests(unittest.TestCase):
    IMAGE = "sha256:" + "a" * 64

    def test_omp_seed_uses_engine_volume_and_exports_only_agent_db(self):
        with tempfile.TemporaryDirectory() as temporary:
            seed_root = Path(temporary) / "seeds"
            calls: list[list[str]] = []

            def fake_run(argv, check=False, **kwargs):
                del check, kwargs
                command = [str(item) for item in argv]
                calls.append(command)
                if command[1:3] == ["volume", "inspect"]:
                    return subprocess.CompletedProcess(command, 1)
                if command[1] == "run" and "/bin/sh" in command:
                    export_mount = next(
                        item for item in command if "dst=/seed-export" in item
                    )
                    source = next(
                        field.split("=", 1)[1]
                        for field in export_mount.split(",")
                        if field.startswith("src=")
                    )
                    (Path(source) / "agent.db").write_bytes(b"sqlite-auth-fixture")
                return subprocess.CompletedProcess(command, 0)

            with (
                mock.patch.object(
                    CLEAN_ROOM_TOOL.subprocess, "run", side_effect=fake_run
                ),
                mock.patch.object(CLEAN_ROOM_TOOL.sys, "platform", "darwin"),
            ):
                CLEAN_ROOM_TOOL.seed(
                    "podman",
                    {"images": {"omp": {"image_id": self.IMAGE}}},
                    "omp",
                    "omp-fresh",
                    seed_root,
                )

            destination = seed_root / "omp-fresh"
            interactive = next(call for call in calls if "--interactive" in call)
            mounts = [
                interactive[index + 1]
                for index, value in enumerate(interactive)
                if value == "--mount"
            ]
            self.assertEqual(
                mounts,
                [
                    "type=volume,src=highlander-seed-omp-fresh,"
                    "dst=/seed-output,rw"
                ],
            )
            self.assertEqual(interactive[interactive.index("--user") + 1], "0:0")
            self.assertNotIn(str(destination), " ".join(interactive))
            self.assertEqual(
                sorted(path.name for path in destination.iterdir()), ["agent.db"]
            )
            self.assertEqual(
                stat.S_IMODE(os.stat(destination).st_mode),
                0o700,
            )
            self.assertEqual(
                stat.S_IMODE(os.stat(destination / "agent.db").st_mode),
                0o600,
            )
            self.assertIn(
                ["podman", "volume", "rm", "highlander-seed-omp-fresh"],
                calls,
            )
            xattr_deletes = [
                call for call in calls if call[:2] == ["/usr/bin/xattr", "-d"]
            ]
            self.assertEqual(
                [call[2] for call in xattr_deletes],
                ["user.containers.override_stat", "security.selinux"],
            )


if __name__ == "__main__":
    unittest.main()

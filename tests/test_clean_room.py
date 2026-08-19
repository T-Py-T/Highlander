import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from highlander.cleanroom import CleanRoom
from highlander.engine import MatchRunner
from highlander.model import SpecError


class CleanRoomMatchTests(unittest.TestCase):
    OMP_IMAGE = "sha256:" + "1" * 64
    OPENCODE_IMAGE = "sha256:" + "2" * 64
    EVALUATOR_IMAGE = "sha256:" + "3" * 64
    CODEX_IMAGE = "sha256:" + "4" * 64
    HERMES_IMAGE = "sha256:" + "5" * 64
    NANOBOT_IMAGE = "sha256:" + "6" * 64

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = self.root / "arena"
        self.repository.mkdir()
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=self.repository,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Highlander Tests"],
            cwd=self.repository,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "highlander@example.invalid"],
            cwd=self.repository,
            check=True,
        )
        (self.repository / "example.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.repository, check=True)
        subprocess.run(
            ["git", "commit", "-m", "base"],
            cwd=self.repository,
            check=True,
            capture_output=True,
        )
        self.task = self.root / "task.md"
        self.task.write_text("Create harness.txt with your harness name.\n", encoding="utf-8")
        self.overlay = self.root / "hidden-evaluator"
        self.overlay.mkdir()
        (self.overlay / "evaluator-check.txt").write_text(
            "controller-only\n", encoding="utf-8"
        )
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self._write_fake_runtime()
        self.old_path = os.environ.get("PATH", "")
        self.old_seed_root = os.environ.get("HIGHLANDER_SEED_ROOT")
        os.environ["PATH"] = f"{self.bin_dir}{os.pathsep}{self.old_path}"
        os.environ["HIGHLANDER_SEED_ROOT"] = str(self.root / "seeds")

    def tearDown(self):
        os.environ["PATH"] = self.old_path
        if self.old_seed_root is None:
            os.environ.pop("HIGHLANDER_SEED_ROOT", None)
        else:
            os.environ["HIGHLANDER_SEED_ROOT"] = self.old_seed_root
        self.temporary.cleanup()

    def _write_fake_runtime(self):
        runtime = self.bin_dir / "docker"
        runtime.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import json
                import sys
                from pathlib import Path

                OMP = {self.OMP_IMAGE!r}
                OPENCODE = {self.OPENCODE_IMAGE!r}
                EVALUATOR = {self.EVALUATOR_IMAGE!r}
                CODEX = {self.CODEX_IMAGE!r}
                HERMES = {self.HERMES_IMAGE!r}
                NANOBOT = {self.NANOBOT_IMAGE!r}

                args = sys.argv[1:]
                if args == ["--version"]:
                    print("Docker version fake-1")
                    raise SystemExit(0)
                if args and args[0] == "info":
                    print("fake clean-room runtime")
                    raise SystemExit(0)
                if args[:2] == ["image", "inspect"]:
                    image = args[2]
                    harness = {{
                        OMP: "omp",
                        OPENCODE: "opencode",
                        EVALUATOR: "evaluator",
                        CODEX: "codex",
                        HERMES: "hermes",
                        NANOBOT: "nanobot",
                    }}[image]
                    labels = {{
                        "io.highlander.harness": harness,
                        "io.highlander.profile": "clean-core",
                        "io.highlander.version": "test-1",
                    }}
                    print(json.dumps([{{
                        "Id": image,
                        "RepoDigests": [],
                        "Architecture": "arm64",
                        "Os": "linux",
                        "Config": {{"Labels": labels}},
                    }}]))
                    raise SystemExit(0)
                if args and args[0] == "inspect":
                    raise SystemExit(1)
                if args and args[0] == "rm":
                    raise SystemExit(0)
                if args and args[0] == "run":
                    workspace = None
                    for index, value in enumerate(args):
                        if value == "--mount" and index + 1 < len(args):
                            mount = args[index + 1]
                            if "dst=/workspace" in mount:
                                fields = dict(item.split("=", 1) for item in mount.split(",") if "=" in item)
                                workspace = Path(fields["src"])
                    image_index = next(index for index, value in enumerate(args) if value in {{OMP, OPENCODE, EVALUATOR, CODEX, HERMES, NANOBOT}})
                    command = args[image_index + 1:]
                    if args[image_index] != EVALUATOR:
                        harness = {{
                            OMP: "omp",
                            OPENCODE: "opencode",
                            CODEX: "codex",
                            HERMES: "hermes",
                            NANOBOT: "nanobot",
                        }}[args[image_index]]
                        (workspace / "harness.txt").write_text(harness + "\\n", encoding="utf-8")
                        print(json.dumps({{
                            "type": "session",
                            "model": "fake/exact-model-v1",
                            "provider": "fake-provider",
                            "reasoning": "low",
                            "upstream_id": "fake/exact-model-v1",
                            "endpoint_or_deployment": "local-fixture",
                            "region": "local",
                        }}))
                        print(json.dumps({{"type": "text", "text": "completed by " + harness}}))
                    else:
                        if not (workspace / "evaluator-check.txt").is_file():
                            print("hidden evaluator overlay missing", file=sys.stderr)
                            raise SystemExit(7)
                        print("evaluator passed: " + " ".join(command))
                    raise SystemExit(0)
                print("unexpected fake docker invocation: " + repr(args), file=sys.stderr)
                raise SystemExit(64)
                """
            ),
            encoding="utf-8",
        )
        runtime.chmod(0o755)

    def write_spec(self, match_id="clean-match", session="headless"):
        payload = {
            "schema_version": 1,
            "match_id": match_id,
            "lane": "controlled_efficacy",
            "arena": {
                "repository": str(self.repository),
                "base_ref": "main",
                "clean_room": {
                    "runtime": "docker",
                    "profile": "clean-core",
                    "evaluator_image": self.EVALUATOR_IMAGE,
                    "network": "bridge",
                    "cpus": 2,
                    "memory_mb": 2048,
                    "pids_limit": 256,
                    "tmpfs_mb": 512,
                    "retain_workspaces": False,
                },
            },
            "task": {"path": str(self.task)},
            "control_profile": {
                "model": {
                    "requested_id": "fake/exact-model-v1",
                    "upstream_id": "fake/exact-model-v1",
                    "provider_id": "fake-provider",
                    "endpoint_or_deployment": "local-fixture",
                    "region": "local",
                    "auth_route": "none",
                },
                "reasoning": {"requested": "low", "wire_parameter": "low"},
                "fallback_policy": "forbidden",
                "auxiliary_model_policy": "disabled",
                "limits": {
                    "wall_time_seconds": 10,
                    "external_model_request_cap": 10,
                },
                "proof_required": ["configured", "runtime", "provider_wire"],
            },
            "contenders": [
                {
                    "id": "omp-clean",
                    "adapter": "omp",
                    "options": {
                        "approval_mode": "yolo",
                        "image": self.OMP_IMAGE,
                    },
                },
                {
                    "id": "opencode-clean",
                    "adapter": "opencode",
                    "options": {"pure": True, "image": self.OPENCODE_IMAGE},
                },
            ],
            "evaluation": {
                "overlay": str(self.overlay),
                "commands": [
                    {
                        "id": "tests",
                        "argv": ["go", "test", "./..."],
                        "timeout_seconds": 10,
                    }
                ]
            },
            "session": {"adapter": session},
            "output_root": str(self.root / "runs"),
        }
        path = self.root / f"{match_id}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_clean_room_match_retains_raw_results_and_destroys_trial_state(self):
        runner = MatchRunner.from_file(self.write_spec())
        plan = runner.plan()
        self.assertTrue(plan["safety"]["disposable_containers"])
        self.assertFalse(plan["safety"]["publication_available"])
        self.assertEqual(plan["arena"]["isolation"], "independent_disposable_clone")
        for trial in plan["trials"]:
            self.assertEqual(trial["clean_room"]["image_id"], trial["options"]["image"])
            self.assertNotIn(str(Path.home()), json.dumps(trial["invocation"]))

        result = runner.execute(reviewed_plan=plan)

        self.assertEqual(result["state"], "COMPLETE")
        run_dir = self.root / "runs" / "clean-match"
        for contender in ("omp-clean", "opencode-clean"):
            trial_dir = run_dir / "trials" / contender / "attempt-001"
            cleanup = json.loads((trial_dir / "cleanup.json").read_text(encoding="utf-8"))
            self.assertTrue(cleanup["container_reconciled"])
            self.assertTrue(cleanup["workspace_removed"])
            self.assertFalse(Path(cleanup["workspace"]).exists())
            patch = (trial_dir / "repository" / "diff.patch").read_text(encoding="utf-8")
            self.assertIn("harness.txt", patch)
            self.assertNotIn("evaluator-check.txt", patch)
            validation = json.loads(
                (trial_dir / "validation" / "summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(validation["status"], "passed")
            self.assertTrue((trial_dir / "native" / "harness-output.jsonl").is_file())

    def test_clean_room_rejects_unpinned_images(self):
        spec_path = self.write_spec(match_id="unpinned")
        payload = json.loads(spec_path.read_text(encoding="utf-8"))
        payload["contenders"][0]["options"]["image"] = "highlander/omp:latest"
        spec_path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(SpecError, "pinned image"):
            MatchRunner.from_file(spec_path)

    def test_nanobot_seed_probe_accepts_only_the_isolated_oauth_file(self):
        seed = self.root / "seeds" / "nanobot-subscription"
        seed.mkdir(parents=True)
        (seed / "oauth.json").write_text("{}\n", encoding="utf-8")
        clean_room = CleanRoom(
            {
                "runtime": "docker",
                "profile": "clean-core",
                "evaluator_image": self.EVALUATOR_IMAGE,
                "network": "bridge",
                "cpus": 2,
                "memory_mb": 2048,
                "pids_limit": 256,
                "tmpfs_mb": 512,
                "retain_workspaces": False,
            }
        )

        result = clean_room.inspect_seed(
            "nanobot", "nanobot-subscription", required=True
        )

        self.assertTrue(result["available"])
        self.assertEqual(result["imported_file"], "oauth.json")

    def test_codex_and_hermes_seed_probes_accept_only_isolated_auth_files(self):
        clean_room = CleanRoom(
            {
                "runtime": "docker",
                "profile": "clean-core",
                "evaluator_image": self.EVALUATOR_IMAGE,
                "network": "bridge",
                "cpus": 2,
                "memory_mb": 2048,
                "pids_limit": 256,
                "tmpfs_mb": 512,
                "retain_workspaces": False,
            }
        )
        for harness in ("codex", "hermes"):
            profile = f"{harness}-subscription"
            seed = self.root / "seeds" / profile
            seed.mkdir(parents=True)
            (seed / "auth.json").write_text("{}\n", encoding="utf-8")

            result = clean_room.inspect_seed(harness, profile, required=True)

            self.assertTrue(result["available"])
            self.assertEqual(result["imported_file"], "auth.json")

    @unittest.skipUnless(
        os.environ.get("HIGHLANDER_TEST_TMUX") == "1", "opt-in tmux integration"
    )
    def test_tmux_clean_room_match_uses_the_same_disposable_path(self):
        runner = MatchRunner.from_file(
            self.write_spec(match_id="clean-tmux", session="tmux")
        )
        result = runner.execute(reviewed_plan=runner.plan())
        self.assertEqual(result["state"], "COMPLETE")
        self.assertTrue(result["session_cleanup"]["session_closed"])
        self.assertTrue(
            all(trial["qualification"] == "qualified" for trial in result["trials"])
        )

    def test_match_generator_resolves_the_image_lock_into_a_reviewable_spec(self):
        lock_path = self.root / "images.lock.json"
        lock_path.write_text(
            json.dumps(
                {
                    "runtime": "docker",
                    "profile": "clean-core",
                    "images": {
                        "omp": {"image_id": self.OMP_IMAGE},
                        "opencode": {"image_id": self.OPENCODE_IMAGE},
                        "codex": {"image_id": self.CODEX_IMAGE},
                        "hermes": {"image_id": self.HERMES_IMAGE},
                        "nanobot": {"image_id": self.NANOBOT_IMAGE},
                        "evaluator": {"image_id": self.EVALUATOR_IMAGE},
                    },
                }
            ),
            encoding="utf-8",
        )
        output = self.root / "generated.json"
        script = Path(__file__).resolve().parents[1] / "tools" / "clean-room.py"
        result = subprocess.run(
            [
                "python3",
                str(script),
                "--runtime",
                "docker",
                "--lock",
                str(lock_path),
                "new-match",
                "--match-id",
                "generated-clean-match",
                "--arena",
                str(self.repository),
                "--base-ref",
                "main",
                "--task",
                str(self.task),
                "--model",
                "fake/exact-model-v1",
                "--provider",
                "fake-provider",
                "--endpoint",
                "local-fixture",
                "--region",
                "local",
                "--reasoning",
                "low",
                "--auth-route",
                "none",
                "--session",
                "headless",
                "--evaluation-overlay",
                str(self.overlay),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = MatchRunner.from_file(output).plan()
        self.assertEqual(plan["evaluator_image"]["image_id"], self.EVALUATOR_IMAGE)
        self.assertEqual(
            [trial["clean_room"]["image_id"] for trial in plan["trials"]],
            [
                self.OMP_IMAGE,
                self.OPENCODE_IMAGE,
                self.CODEX_IMAGE,
                self.HERMES_IMAGE,
                self.NANOBOT_IMAGE,
            ],
        )
        self.assertEqual(plan["evaluation"]["overlay_files"], 1)


if __name__ == "__main__":
    unittest.main()

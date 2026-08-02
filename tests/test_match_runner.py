import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from highlander.engine import MatchRunner
from highlander.model import HighlanderError, SpecError


class MatchRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = self.root / "target"
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
        self.task.write_text("Fix the deterministic fixture.\n", encoding="utf-8")

    def tearDown(self):
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self.repository,
            check=False,
            capture_output=True,
        )
        self.temporary.cleanup()

    def write_spec(self, match_id="fake-match", contenders=None, session="headless"):
        if contenders is None:
            contenders = [
                {
                    "id": "fake-success",
                    "adapter": "fake",
                    "options": {"behavior": "success"},
                },
                {
                    "id": "fake-failure",
                    "adapter": "fake",
                    "options": {"behavior": "harness_failure"},
                },
            ]
        payload = {
            "schema_version": 1,
            "match_id": match_id,
            "lane": "concurrency",
            "arena": {"repository": str(self.repository), "base_ref": "main"},
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
                    "external_model_request_cap": 1,
                },
                "proof_required": ["configured", "runtime", "provider_wire"],
            },
            "contenders": contenders,
            "session": {"adapter": session},
            "output_root": str(self.root / "runs"),
        }
        spec_path = self.root / f"{match_id}.json"
        spec_path.write_text(json.dumps(payload), encoding="utf-8")
        return spec_path

    def test_dry_run_is_side_effect_free_and_redacted(self):
        runner = MatchRunner.from_file(self.write_spec())
        plan = runner.plan()
        self.assertFalse(Path(plan["run_dir"]).exists())
        self.assertTrue(plan["safety"]["dry_run_default"])
        self.assertFalse(plan["safety"]["credentials_brokered"])
        self.assertEqual(len(plan["trials"]), 2)
        for trial in plan["trials"]:
            self.assertFalse(trial["invocation"]["credential_values_recorded"])
            self.assertEqual(trial["capability"]["harness"]["name"], "fake")

    def test_headless_fake_match_uses_one_prompt_and_retains_evidence(self):
        runner = MatchRunner.from_file(self.write_spec())
        result = runner.execute(reviewed_plan=runner.plan())
        run_dir = self.root / "runs" / "fake-match"
        self.assertEqual(result["state"], "COMPLETE")
        self.assertEqual(result["task_sha256"], result["trials"][0]["task_sha256"])
        self.assertEqual(result["task_sha256"], result["trials"][1]["task_sha256"])
        self.assertEqual(result["trials"][0]["qualification"], "qualified")
        self.assertEqual(
            result["trials"][0]["competitive_outcome"], "protocol_success"
        )
        self.assertEqual(result["trials"][1]["qualification"], "qualified")
        self.assertEqual(
            result["trials"][1]["competitive_outcome"],
            "protocol_harness_failure",
        )
        self.assertGreaterEqual(result["start_skew_ms"], 0)
        for contender in ("fake-success", "fake-failure"):
            trial = run_dir / "trials" / contender / "attempt-001"
            atif = json.loads(
                (trial / "normalized" / "trajectory.atif.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(atif["schema_version"], "ATIF-v1.7")
            self.assertEqual(atif["final_metrics"]["total_cost_usd"], 0)
            cleanup = json.loads((trial / "cleanup.json").read_text(encoding="utf-8"))
            self.assertEqual(
                cleanup["worktree_policy"], "retained_intentionally_for_review"
            )
        manifest = json.loads(
            (run_dir / "artifact-manifest.json").read_text(encoding="utf-8")
        )
        self.assertFalse(
            any(item["path"].startswith("worktrees/") for item in manifest["artifacts"])
        )

    def test_control_divergence_invalidates_without_becoming_a_model_loss(self):
        contenders = [
            {"id": "control", "adapter": "fake", "options": {}},
            {
                "id": "divergent",
                "adapter": "fake",
                "options": {"behavior": "control_violation"},
            },
        ]
        runner = MatchRunner.from_file(
            self.write_spec(match_id="invalid-control", contenders=contenders)
        )
        result = runner.execute(reviewed_plan=runner.plan())
        divergent = next(
            trial for trial in result["trials"] if trial["contender_id"] == "divergent"
        )
        self.assertEqual(divergent["qualification"], "invalid")
        self.assertIn("runtime model diverged", divergent["invalid_reasons"][0])

    @unittest.skipUnless(
        os.environ.get("HIGHLANDER_TEST_TMUX") == "1", "opt-in tmux integration"
    )
    def test_tmux_fake_match(self):
        runner = MatchRunner.from_file(
            self.write_spec(match_id="tmux-fake", session="tmux")
        )
        result = runner.execute(reviewed_plan=runner.plan())
        self.assertEqual(result["state"], "COMPLETE")
        self.assertTrue(result["session_cleanup"]["session_closed"])

    def test_real_adapters_are_plannable_but_execution_blocked(self):
        contenders = [
            {"id": "omp", "adapter": "omp", "options": {}},
            {"id": "opencode", "adapter": "opencode", "options": {}},
        ]
        runner = MatchRunner.from_file(
            self.write_spec(match_id="real-dry-run", contenders=contenders)
        )
        plan = runner.plan()
        commands = {
            trial["adapter"]: trial["invocation"]["argv"]
            for trial in plan["trials"]
        }
        self.assertIn("rpc", commands["omp"])
        self.assertIn("--thinking", commands["omp"])
        self.assertIn("--variant", commands["opencode"])
        with self.assertRaises(HighlanderError):
            runner.execute(reviewed_plan=plan)

    def test_pre_gate_failure_is_invalid_and_cleanup_is_retained(self):
        contenders = [
            {
                "id": "broken-worker",
                "adapter": "fake",
                "options": {"behavior": "pre_gate_failure"},
            },
            {"id": "waiting-worker", "adapter": "fake", "options": {}},
        ]
        runner = MatchRunner.from_file(
            self.write_spec(match_id="pre-gate-failure", contenders=contenders)
        )
        with self.assertRaises(HighlanderError):
            runner.execute(reviewed_plan=runner.plan())
        run_dir = self.root / "runs" / "pre-gate-failure"
        result = json.loads(
            (run_dir / "match-result.json").read_text(encoding="utf-8")
        )
        self.assertEqual(result["state"], "INVALID")
        self.assertTrue(result["session_cleanup"]["session_closed"])
        self.assertTrue((run_dir / "artifact-manifest.json").is_file())
        events = [
            json.loads(line)
            for line in (run_dir / "journal" / "match-events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertEqual(events[-1]["event"], "INVALID_SEALED")

    def test_credential_shaped_options_are_rejected(self):
        contenders = [
            {
                "id": "unsafe",
                "adapter": "fake",
                "options": {"api_key": "must-not-enter-a-match-spec"},
            },
            {"id": "safe", "adapter": "fake", "options": {}},
        ]
        with self.assertRaises(SpecError):
            MatchRunner.from_file(
                self.write_spec(match_id="unsafe-spec", contenders=contenders)
            )

    def test_changed_plan_is_rejected_before_side_effects(self):
        runner = MatchRunner.from_file(self.write_spec(match_id="reviewed-plan"))
        plan = runner.plan()
        self.task.write_text("Changed after review.\n", encoding="utf-8")
        with self.assertRaises(HighlanderError):
            runner.execute(reviewed_plan=plan)
        self.assertFalse((self.root / "runs" / "reviewed-plan").exists())

    def test_worker_options_use_adapter_allowlists(self):
        contenders = [
            {
                "id": "unsafe",
                "adapter": "fake",
                "options": {"harmless_name": "Bearer secret"},
            },
            {"id": "safe", "adapter": "fake", "options": {}},
        ]
        with self.assertRaises(SpecError):
            MatchRunner.from_file(
                self.write_spec(match_id="unsafe-options", contenders=contenders)
            )

    def test_fake_workers_do_not_inherit_provider_credentials(self):
        environment = MatchRunner._worker_environment()
        forbidden_fragments = (
            "API_KEY",
            "AUTH",
            "AWS_",
            "CREDENTIAL",
            "OAUTH",
            "SECRET",
            "TOKEN",
        )
        self.assertFalse(
            any(
                fragment in name.upper()
                for name in environment
                for fragment in forbidden_fragments
            )
        )
        self.assertEqual(environment["PYTHONUNBUFFERED"], "1")


if __name__ == "__main__":
    unittest.main()

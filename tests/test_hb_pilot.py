import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import cast

from highlander.hb_pilot import (
    aggregate_pilot,
    build_host_environment,
    build_host_invocation,
    classify_harnessbench_result,
    matched_block_schedule,
    verify_frozen_protocol,
)


class HarnessBenchPilotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.prompt = self.root / "prompt.txt"
        self.prompt.write_text("Repair the migration.\n", encoding="utf-8")
        self.evidence = self.root / "native"
        self.profile_root = self.root / "profiles"

    def tearDown(self):
        self.temporary.cleanup()

    def test_each_harness_invocation_pins_the_same_model_and_reasoning(self):
        expected = {
            "omp": ("openai-codex/gpt-5.4", "medium"),
            "opencode": ("openai/gpt-5.4", "medium"),
            "codex": ("gpt-5.4", 'model_reasoning_effort="medium"'),
            "hermes": ("gpt-5.4", "medium"),
        }
        for harness, fragments in expected.items():
            invocation = build_host_invocation(
                harness,
                workspace=self.workspace,
                prompt_file=self.prompt,
                evidence_dir=self.evidence,
                timeout_seconds=1200,
            )
            rendered = " ".join(invocation)
            for fragment in fragments:
                self.assertIn(fragment, rendered)
            self.assertNotIn("Repair the migration", rendered)

    def test_invocations_disable_optional_customization_and_are_noninteractive(self):
        omp = build_host_invocation(
            "omp", self.workspace, self.prompt, self.evidence, 1200
        )
        self.assertIn("--no-extensions", omp)
        self.assertIn("--no-skills", omp)
        self.assertIn("--no-rules", omp)
        self.assertIn("--no-session", omp)
        self.assertIn("yolo", omp)

        opencode = build_host_invocation(
            "opencode", self.workspace, self.prompt, self.evidence, 1200
        )
        self.assertIn("--pure", opencode)
        self.assertIn("--auto", opencode)

        codex = build_host_invocation(
            "codex", self.workspace, self.prompt, self.evidence, 1200
        )
        self.assertLess(codex.index("--ask-for-approval"), codex.index("exec"))
        self.assertIn("--ignore-user-config", codex)
        self.assertIn("--ignore-rules", codex)
        self.assertIn("--ephemeral", codex)
        self.assertIn("--skip-git-repo-check", codex)
        self.assertIn("workspace-write", codex)

        hermes = build_host_invocation(
            "hermes", self.workspace, self.prompt, self.evidence, 1200
        )
        self.assertIn("--safe-mode", hermes)
        self.assertIn("--yolo", hermes)
        self.assertIn("--usage-file", hermes)

    def test_host_environment_uses_only_dedicated_profile_and_strips_secrets(self):
        base = {
            "PATH": "/bin:/usr/bin",
            "LANG": "en_US.UTF-8",
            "OPENAI_API_KEY": "must-not-leak",
            "GH_TOKEN": "must-not-leak",
            "SSH_AUTH_SOCK": "/secret/socket",
            "UNRELATED": "must-not-inherit",
            "HARNESSBENCH_TASK_ID": "043-db-migration-safety",
        }
        env = build_host_environment(
            "codex", self.profile_root, self.evidence, base_env=base
        )
        self.assertEqual(env["CODEX_HOME"], str(self.profile_root.resolve() / "codex"))
        self.assertEqual(env["PATH"], base["PATH"])
        self.assertEqual(env["HARNESSBENCH_TASK_ID"], base["HARNESSBENCH_TASK_ID"])
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("GH_TOKEN", env)
        self.assertNotIn("SSH_AUTH_SOCK", env)
        self.assertNotIn("UNRELATED", env)

    def test_schedule_is_seeded_matched_blocks(self):
        schedule = matched_block_schedule(
            ["omp", "opencode", "codex", "hermes"], attempts=3, seed=54043
        )
        self.assertEqual(len(schedule), 12)
        for block in range(1, 4):
            block_rows = [row for row in schedule if row["attempt"] == block]
            self.assertEqual(
                sorted(row["harness_id"] for row in block_rows),
                ["codex", "hermes", "omp", "opencode"],
            )
        self.assertEqual(schedule, matched_block_schedule(
            ["omp", "opencode", "codex", "hermes"], attempts=3, seed=54043
        ))

    def test_result_classification_never_turns_invalid_into_zero(self):
        invalid = classify_harnessbench_result(
            {"adapter_result": {"ok": False, "metadata": {"returncode": 1}}},
            wrapper_execution={"timed_out": False, "returncode": 1},
        )
        self.assertEqual(invalid["qualification"], "invalid")
        self.assertIsNone(invalid["outcome_score"])
        self.assertIsNone(invalid["process_score"])
        self.assertIsNone(invalid["combined_score"])

    def test_valid_result_uses_only_deterministic_outcome_score(self):
        payload = {
            "adapter_result": {"ok": True, "metadata": {"returncode": 0}},
            "oracle_result": {"score": 0.75, "checks": []},
            "scoring": {
                "outcome_score": 0.75,
                "process_score": 1.0,
                "combined_score": 0.875,
                "rubric": {"skipped": True},
            },
        }
        classified = classify_harnessbench_result(
            payload,
            wrapper_execution={"timed_out": False, "returncode": 0},
        )
        self.assertEqual(classified["qualification"], "valid")
        self.assertEqual(classified["outcome_score"], 0.75)
        self.assertIsNone(classified["process_score"])
        self.assertIsNone(classified["combined_score"])
        self.assertEqual(classified["process_status"], "not_evaluated")

    def test_host_adapter_retains_raw_output_and_redacts_prompt_and_profile(self):
        (self.profile_root / "codex").mkdir(parents=True)
        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        fake_codex = fake_bin / "codex"
        fake_codex.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import sys
                print(json.dumps({"type": "tool_call", "tool_name": "shell", "status": "started"}))
                print(json.dumps({"type": "message", "text": "done"}))
                print("warning", file=sys.stderr)
                raise SystemExit(0 if os.environ.get("CODEX_HOME") else 9)
                """
            ),
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)
        script = Path(__file__).resolve().parents[1] / "tools" / "hb-host-adapter.py"
        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
        env["HIGHLANDER_PILOT_PROFILE_ROOT"] = str(self.profile_root)
        result = subprocess.run(
            [
                "python3",
                str(script),
                "--harness",
                "codex",
                "--workspace",
                str(self.workspace),
                "--prompt-file",
                str(self.prompt),
                "--evidence-dir",
                str(self.evidence),
                "--timeout-seconds",
                "30",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tool_call", result.stdout)
        self.assertEqual((self.evidence / "stderr.raw").read_text(), "warning\n")
        invocation = json.loads((self.evidence / "invocation.json").read_text())
        serialized = json.dumps(invocation)
        self.assertIn("<TASK_BYTES_UTF8>", serialized)
        self.assertNotIn("Repair the migration", serialized)
        self.assertNotIn(str(self.profile_root), serialized)
        execution = json.loads((self.evidence / "execution.json").read_text())
        self.assertEqual(execution["returncode"], 0)
        self.assertFalse(execution["timed_out"])
        self.assertEqual(execution["process_metrics"]["event_count"], 2)
        self.assertEqual(execution["process_metrics"]["tool_event_count"], 1)
        self.assertTrue(execution["temporary_home_removed"])

    def test_protocol_verifier_fails_closed_on_hash_drift(self):
        protocol = self.root / "protocol.json"
        protocol.write_text(json.dumps({"protocol_id": "pilot-r1"}) + "\n")
        sidecar = self.root / "protocol.json.sha256"
        sidecar.write_text("0" * 64 + "  protocol.json\n")
        with self.assertRaisesRegex(ValueError, "protocol hash mismatch"):
            verify_frozen_protocol(protocol, sidecar)

    def test_aggregate_reports_variance_without_declaring_a_winner(self):
        rows = [
            {"harness_id": "omp", "qualification": "valid", "outcome_score": 0.8, "elapsed_seconds": 10, "tool_event_count": 2},
            {"harness_id": "omp", "qualification": "valid", "outcome_score": 1.0, "elapsed_seconds": 20, "tool_event_count": 4},
            {"harness_id": "codex", "qualification": "invalid", "outcome_score": None, "elapsed_seconds": 1, "tool_event_count": 0},
            {"harness_id": "nanobot", "qualification": "unavailable", "outcome_score": None, "elapsed_seconds": None, "tool_event_count": None},
        ]
        summary = aggregate_pilot(rows, expected_attempts=2)
        harnesses = cast(list[dict[str, object]], summary["harnesses"])
        omp = next(row for row in harnesses if row["harness_id"] == "omp")
        codex = next(row for row in harnesses if row["harness_id"] == "codex")
        nanobot = next(row for row in harnesses if row["harness_id"] == "nanobot")
        self.assertEqual(omp["mean_outcome"], 0.9)
        self.assertEqual(omp["population_stddev"], 0.1)
        self.assertEqual(omp["valid_trials"], 2)
        self.assertEqual(codex["invalid_trials"], 1)
        self.assertEqual(nanobot["unavailable_trials"], 1)
        self.assertIsNone(summary["winner"])
        self.assertEqual(summary["claim_status"], "underpowered_single_task_pilot")

    def test_aggregate_rejects_valid_result_without_numeric_score(self):
        rows = [
            {
                "harness_id": "omp",
                "qualification": "valid",
                "outcome_score": None,
            }
        ]
        with self.assertRaisesRegex(ValueError, "numeric outcome_score"):
            aggregate_pilot(rows, expected_attempts=1)


if __name__ == "__main__":
    unittest.main()

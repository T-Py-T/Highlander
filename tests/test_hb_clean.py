import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from highlander.cleanroom import extract_control_proof
from highlander.hb_clean import SUPPORTED_HARNESSES, build_container_command
from highlander.hb_season_run import SOURCE_FILES, freeze_protocol


class CleanHarnessBenchTests(unittest.TestCase):
    def test_token_usage_reasoning_counter_is_not_runtime_reasoning(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "native.jsonl"
            output.write_text(
                json.dumps(
                    {
                        "type": "step-finish",
                        "tokens": {"input": 282, "output": 10, "reasoning": 0},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            proof, _ = extract_control_proof(
                output,
                {
                    "model": "gpt-5.6-luna",
                    "provider": "openai",
                    "reasoning": "medium",
                    "upstream_id": None,
                    "endpoint_or_deployment": None,
                    "region": None,
                },
            )

            self.assertIsNone(proof["observed"]["reasoning"])
            self.assertFalse(proof["runtime_conflict"])

    def test_partial_matching_identity_is_not_a_control_conflict(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "native.jsonl"
            output.write_text(
                json.dumps(
                    {
                        "model": "gpt-5.6-luna",
                        "provider": "openai-codex",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            proof, _ = extract_control_proof(
                output,
                {
                    "model": "gpt-5.6-luna",
                    "provider": "openai-codex",
                    "reasoning": "medium",
                    "upstream_id": None,
                    "endpoint_or_deployment": None,
                    "region": None,
                },
            )

            self.assertFalse(proof["runtime_verified"])
            self.assertFalse(proof["runtime_conflict"])
            self.assertEqual(proof["runtime_conflicts"], {})

    def test_observed_string_identity_mismatch_is_a_control_conflict(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "native.jsonl"
            output.write_text(
                json.dumps(
                    {
                        "model": "gpt-5.4",
                        "provider": "openai-codex",
                        "reasoning": "medium",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            proof, _ = extract_control_proof(
                output,
                {
                    "model": "gpt-5.6-luna",
                    "provider": "openai-codex",
                    "reasoning": "medium",
                    "upstream_id": None,
                    "endpoint_or_deployment": None,
                    "region": None,
                },
            )

            self.assertFalse(proof["runtime_verified"])
            self.assertTrue(proof["runtime_conflict"])
            self.assertEqual(
                proof["runtime_conflicts"]["model"],
                {"expected": "gpt-5.6-luna", "observed": "gpt-5.4"},
            )

    def test_every_command_uses_container_workspace_and_frozen_model(self):
        for harness_id in SUPPORTED_HARNESSES:
            lane = {
                "configured_model_id": (
                    "openai-codex/gpt-5.6-luna"
                    if harness_id in {"omp", "nanobot"}
                    else "openai/gpt-5.6-luna"
                    if harness_id == "opencode"
                    else "gpt-5.6-luna"
                ),
                "provider_id": "openai" if harness_id == "opencode" else "openai-codex",
                "reasoning": "medium",
                "wire_reasoning": "medium",
            }
            command = build_container_command(harness_id, lane, 1200)
            rendered = " ".join(command)
            self.assertIn("gpt-5.6-luna", rendered)
            self.assertNotIn(str(Path.home()), rendered)
            if harness_id != "atomic":
                self.assertIn("/workspace", rendered)

    def test_protocol_freeze_hashes_sources_tasks_images_and_schedule(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "runner"
            upstream = base / "upstream"
            root.mkdir()
            upstream.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "init", "-b", "main"], cwd=upstream, check=True, capture_output=True)
            for repository in (root, upstream):
                subprocess.run(["git", "config", "user.name", "Highlander Tests"], cwd=repository, check=True)
                subprocess.run(["git", "config", "user.email", "highlander@example.invalid"], cwd=repository, check=True)
            for relative in SOURCE_FILES:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"fixture {relative}\n", encoding="utf-8")
            task_dir = upstream / "tasks" / "task-hard"
            (task_dir / "fixtures").mkdir(parents=True)
            (task_dir / "fixtures" / "input.txt").write_text("input\n", encoding="utf-8")
            (task_dir / "prompt.txt").write_text("work in $WORKSPACE\n", encoding="utf-8")
            (task_dir / "oracle_grade.py").write_text("def score_workspace(path): return {'outcome_score': 1}\n", encoding="utf-8")
            (task_dir / "task.yaml").write_text("task_id: task-hard\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=upstream, check=True)
            subprocess.run(["git", "commit", "-m", "upstream"], cwd=upstream, check=True, capture_output=True)
            contenders = [
                {"id": harness_id, "version": "1", "role": "control" if harness_id == "omp" else "challenger"}
                for harness_id in SUPPORTED_HARNESSES
            ]
            manifest = {
                "schema_version": 1,
                "season_id": "season-hard-r1",
                "pack_id": "pack-hard",
                "upstream": {"repository": "https://example.invalid/upstream"},
                "attempts_per_task": 3,
                "tasks": [{"id": "task-hard", "bundle_sha256": "fixture"}],
                "contenders": contenders,
                "execution_stages": [{"id": "hardest-first", "task_ids": ["task-hard"]}],
                "scoring": {"primary": "mean_of_per_task_mean_valid_outcome"},
            }
            manifest_path = root / "benchmark-packs" / "pack.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            images = {name: {"image_id": f"sha256:{index:064x}"} for index, name in enumerate((*SUPPORTED_HARNESSES, "evaluator"), 1)}
            lock_path = root / ".highlander" / "images.lock.json"
            lock_path.parent.mkdir()
            lock_path.write_text(json.dumps({"images": images}), encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "runner"], cwd=root, check=True, capture_output=True)
            output = root / "protocols" / "season.json"

            result = freeze_protocol(
                root=root,
                manifest_path=manifest_path,
                upstream=upstream,
                image_lock_path=lock_path,
                output=output,
            )

            protocol = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["calls"], 18)
            self.assertEqual(len(protocol["trial_order"]), 18)
            self.assertEqual(protocol["tasks"][0]["oracle_sha256"], protocol["tasks"][0]["file_hashes"]["oracle_grade.py"])
            self.assertEqual(protocol["runtime"]["images"]["nanobot"], images["nanobot"]["image_id"])
            self.assertTrue(
                all(
                    lane["expected_runtime_reasoning"] == "medium"
                    for lane in protocol["harnesses"]
                )
            )
            self.assertTrue(output.with_suffix(".json.sha256").is_file())


if __name__ == "__main__":
    unittest.main()

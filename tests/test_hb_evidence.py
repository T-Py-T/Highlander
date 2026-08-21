import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from highlander.hb_evidence import (
    PilotEvidenceError,
    export_pilot_bundle,
    verify_pilot_bundle,
)


class HarnessBenchEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.runner = self.root / "runner"
        self.runner.mkdir()
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=self.runner,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Highlander Tests"],
            cwd=self.runner,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "highlander@example.invalid"],
            cwd=self.runner,
            check=True,
        )
        (self.runner / "README.md").write_text("runner\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.runner, check=True)
        subprocess.run(
            ["git", "commit", "-m", "base"],
            cwd=self.runner,
            check=True,
            capture_output=True,
        )
        self.source = self.root / "private" / "pilot-r1"
        self._write_source()

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def _write_json(path: Path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _manifest(root: Path):
        files = []
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if path.name == "artifact-manifest.json":
                continue
            raw = path.read_bytes()
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
        HarnessBenchEvidenceTests._write_json(
            root / "artifact-manifest.json",
            {"schema_version": 1, "generated_at": "2026-08-21T00:00:00Z", "files": files},
        )

    def _write_source(self):
        trial = self.source / "trials" / "001-omp-attempt-001"
        native = trial / "native"
        native.mkdir(parents=True)
        stdout = [
            {"type": "tool_execution_start", "toolName": "read"},
            {"type": "tool_execution_update", "toolName": "read"},
            {"type": "tool_execution_end", "toolName": "read"},
            {
                "type": "message_end",
                "message": {
                    "role": "assistant",
                    "model": "gpt-5.4",
                    "provider": "openai-codex",
                    "usage": {
                        "input": 100,
                        "output": 20,
                        "cacheRead": 5,
                        "cacheWrite": 0,
                        "totalTokens": 125,
                        "reasoningTokens": 3,
                        "cost": {"total": 0.01},
                    },
                },
            },
        ]
        (native / "stdout.raw").write_text(
            "\n".join(json.dumps(row) for row in stdout)
            + f"\nworkspace={Path.home()}/private/workspace\n",
            encoding="utf-8",
        )
        (native / "stderr.raw").write_text("", encoding="utf-8")
        self._write_json(
            native / "execution.json",
            {
                "returncode": 0,
                "timed_out": False,
                "elapsed_seconds": 12.5,
                "operator_interventions": 0,
            },
        )
        self._write_json(
            trial / "result.json",
            {
                "protocol_id": "pilot-r1",
                "task_id": "043-db-migration-safety",
                "harness_id": "omp",
                "attempt": 1,
                "sequence": 1,
                "qualification": "valid",
                "outcome_score": 0.9,
                "process_score": None,
                "combined_score": None,
                "elapsed_seconds": 12.5,
                "tool_event_count": 3,
                "operator_interventions": 0,
            },
        )
        self._manifest(trial)
        self._write_json(
            self.source / "protocol.json",
            {
                "protocol_id": "pilot-r1",
                "attempts_per_harness_task": 1,
                "task": {"id": "043-db-migration-safety"},
                "claim_boundary": "single-task pilot",
                "harnesses": [{"id": "omp", "configured_model_id": "openai-codex/gpt-5.4"}],
            },
        )
        (self.source / "protocol.json.sha256").write_text("fixture\n", encoding="utf-8")
        self._write_json(
            self.source / "summary.json",
            {
                "protocol_id": "pilot-r1",
                "trial_rows": [json.loads((trial / "result.json").read_text())],
            },
        )
        (self.source / "report.md").write_text("first pass\n", encoding="utf-8")
        self._manifest(self.source)

    def test_export_redacts_paths_and_normalizes_process_and_usage(self):
        output = self.root / "public" / "pilot-r1"
        verified = export_pilot_bundle(self.source, output, self.runner)
        self.assertEqual(verified["status"], "verified")
        result = json.loads(
            (output / "trials/001-omp-attempt-001/result.json").read_text()
        )
        self.assertEqual(result["process_observations"]["tool_invocation_count"], 1)
        self.assertEqual(result["usage_normalized"]["total_tokens"], 125)
        self.assertNotIn("tool_event_count", result)
        all_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in output.rglob("*")
            if path.is_file()
        )
        self.assertNotIn(str(Path.home()), all_text)
        self.assertIn("<HOME>", all_text)
        self.assertTrue((output / "results.jsonl").is_file())
        leaderboard = json.loads((output / "leaderboard.json").read_text())
        self.assertFalse(leaderboard["ranking_permitted"])
        self.assertIsNone(leaderboard["winner"])
        verify_pilot_bundle(output)

    def test_export_rejects_oauth_json_values(self):
        leaked = self.source / "trials/001-omp-attempt-001/native/stderr.raw"
        leaked.write_text('{"access_token":"definitely-secret-value"}\n')
        self._manifest(leaked.parent.parent)
        self._manifest(self.source)
        with self.assertRaisesRegex(PilotEvidenceError, "oauth_token"):
            export_pilot_bundle(self.source, self.root / "public" / "leaked", self.runner)


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from highlander.hb_evidence import (
    PilotEvidenceError,
    export_pilot_bundle,
    export_season_bundle,
    verify_pilot_bundle,
    verify_season_bundle,
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
        generated = (
            self.source
            / "trials/001-omp-attempt-001/workspace-final/__pycache__/client.cpython-314.pyc"
        )
        generated.parent.mkdir(parents=True)
        generated.write_bytes(b"compiled-path=" + str(Path.home()).encode("utf-8"))
        worktree_git = (
            self.source
            / "trials/001-omp-attempt-001/workspace-final/.git/config"
        )
        worktree_git.parent.mkdir(parents=True)
        worktree_git.write_text("[core]\nrepositoryformatversion = 0\n", encoding="utf-8")
        self._manifest(self.source / "trials/001-omp-attempt-001")
        self._manifest(self.source)
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
        self.assertFalse(
            (
                output
                / "trials/001-omp-attempt-001/workspace-final/__pycache__/client.cpython-314.pyc"
            ).exists()
        )
        redaction = json.loads((output / "redaction-report.json").read_text())
        self.assertEqual(redaction["generated_cache_artifacts_omitted"], 1)
        self.assertEqual(redaction["worktree_vcs_artifacts_omitted"], 1)
        self.assertFalse(
            (
                output / "trials/001-omp-attempt-001/workspace-final/.git"
            ).exists()
        )
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

    def test_export_redacts_provider_encrypted_payload_before_secret_scan(self):
        stdout = self.source / "trials/001-omp-attempt-001/native/stdout.raw"
        rows = stdout.read_text(encoding="utf-8")
        opaque = "psk-" + "A" * 80
        nested_opaque = "psk-" + "B" * 80
        stdout.write_text(
            rows
            + json.dumps(
                {
                    "type": "response_metadata",
                    "encrypted_content": opaque,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        with stdout.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "type": "nested_response_metadata",
                        "payload": json.dumps(
                            {
                                "nested": json.dumps(
                                    {"encrypted_content": nested_opaque}
                                )
                            }
                        ),
                    }
                )
                + "\n"
            )
        self._manifest(stdout.parent.parent)
        self._manifest(self.source)

        output = self.root / "public" / "provider-redacted"
        export_pilot_bundle(self.source, output, self.runner)

        exported = (
            output / "trials/001-omp-attempt-001/native/stdout.raw"
        ).read_text(encoding="utf-8")
        self.assertNotIn(opaque, exported)
        self.assertNotIn(nested_opaque, exported)
        self.assertIn("<PROVIDER_ENCRYPTED_PAYLOAD_REDACTED>", exported)
        report = json.loads((output / "redaction-report.json").read_text())
        self.assertEqual(report["provider_encrypted_payloads_redacted"], 2)

    def test_season_export_rebuilds_ranked_leaderboard(self):
        source = self.root / "private" / "season-r1"
        trial = source / "trials" / "001-task-a-omp-a01-r01"
        native = trial / "native"
        native.mkdir(parents=True)
        (native / "stdout.raw").write_text(
            json.dumps(
                {
                    "type": "message_end",
                    "message": {
                        "role": "assistant",
                        "model": "gpt-5.6-luna",
                        "provider": "openai-codex",
                        "usage": {"input": 10, "output": 5, "totalTokens": 15},
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (native / "stderr.raw").write_text("", encoding="utf-8")
        self._write_json(
            native / "execution.json",
            {"returncode": 0, "timed_out": False, "elapsed_seconds": 7.5},
        )
        row = {
            "schema_version": 1,
            "run_id": "season-r1-task-a-omp-a01-r01",
            "season_id": "season-r1",
            "task_id": "task-a",
            "harness_id": "omp",
            "attempt": 1,
            "retry": 1,
            "sequence": 1,
            "qualification": "valid",
            "outcome_score": 0.75,
            "elapsed_seconds": 7.5,
            "intervention_count": 0,
            "process_score": None,
            "combined_score": None,
        }
        self._write_json(trial / "result.json", row)
        self._manifest(trial)
        season_manifest = {
            "schema_version": 1,
            "season_id": "season-r1",
            "pack_id": "pack-r1",
            "attempts_per_task": 1,
            "tasks": [{"id": "task-a"}],
            "contenders": [{"id": "omp"}],
            "scoring": {"primary": "mean_of_per_task_mean_valid_outcome"},
        }
        self._write_json(source / "season-manifest.json", season_manifest)
        self._write_json(
            source / "protocol.json",
            {"protocol_id": "season-r1", "claim_boundary": "one frozen fixture"},
        )
        (source / "protocol.json.sha256").write_text("fixture\n", encoding="utf-8")
        self._write_json(
            source / "summary.json",
            {
                "protocol_id": "season-r1",
                "protocol_sha256": "fixture",
                "updated_at": "2026-08-30T00:00:00Z",
                "trial_rows": [row],
            },
        )
        (source / "leaderboard.md").write_text("first pass\n", encoding="utf-8")
        (source / "results.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
        self._manifest(source)

        output = self.root / "public" / "season-r1"
        verified = export_season_bundle(source, output, self.runner)

        self.assertEqual(verified["season_status"], "complete")
        leaderboard = json.loads((output / "leaderboard.json").read_text())
        self.assertEqual(leaderboard["contenders"][0]["rank"], 1)
        self.assertEqual(leaderboard["contenders"][0]["metrics"]["overall_outcome"], 0.75)
        verify_season_bundle(output)


if __name__ == "__main__":
    unittest.main()

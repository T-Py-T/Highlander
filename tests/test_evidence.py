import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from highlander.evidence import (
    EvidenceExportError,
    export_public_bundle,
    verify_public_bundle,
)


class PublicEvidenceTests(unittest.TestCase):
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
        self.source = self.root / "source" / "fake-t002"
        self.source.mkdir(parents=True)
        self._write_source_bundle()

    def tearDown(self):
        self.temporary.cleanup()

    def _write_source_bundle(self):
        plan = {
            "match_id": "fake-t002",
            "plan_hash": "b" * 64,
            "run_dir": str(self.source),
            "arena": {
                "repository": str(self.runner),
                "base_sha": "c" * 40,
                "source_worktree_dirty": False,
            },
            "task": {
                "source": str(self.runner / "tasks" / "T002.md"),
                "sha256": "a" * 64,
            },
            "trials": [
                {
                    "contender_id": "fake-success",
                    "adapter": "fake",
                    "worktree": str(self.source / "worktrees" / "fake-success"),
                }
            ],
        }
        result = {
            "match_id": "fake-t002",
            "state": "COMPLETE",
            "completed_at": "2026-08-19T12:00:00Z",
            "start_skew_ms": 0.2,
            "trials": [
                {
                    "contender_id": "fake-success",
                    "qualification": "qualified",
                    "competitive_outcome": "protocol_success",
                    "invalid_reasons": [],
                }
            ],
        }
        artifacts = {
            "execution-plan.json": json.dumps(plan, indent=2) + "\n",
            "match-result.json": json.dumps(result, indent=2) + "\n",
            "native/transcript.json": json.dumps(
                {"message": f"evidence at {self.source}", "cost": 0}
            )
            + "\n",
        }
        records = []
        for name, text in artifacts.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            raw = path.read_bytes()
            records.append(
                {
                    "path": name,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                }
            )
        (self.source / "artifact-manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "generated_at": result["completed_at"],
                    "artifacts": records,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def test_export_is_path_safe_commit_bound_and_self_verifying(self):
        output = self.root / "public" / "fake-t002"

        verified = export_public_bundle(self.source, output, self.runner)

        self.assertEqual(verified["status"], "verified")
        provenance = json.loads(
            (output / "runner-provenance.json").read_text(encoding="utf-8")
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.runner,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(provenance["runner"]["commit"], head)
        self.assertTrue(provenance["runner"]["worktree_clean"])
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in output.rglob("*")
            if path.is_file()
        )
        self.assertNotIn(str(self.root), text)
        manifest = json.loads(
            (output / "artifact-manifest.json").read_text(encoding="utf-8")
        )
        self.assertFalse(
            any("worktrees" in item["path"] for item in manifest["artifacts"])
        )
        verify_public_bundle(output)

    def test_export_rejects_a_dirty_runner(self):
        (self.runner / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(EvidenceExportError, "must be clean"):
            export_public_bundle(
                self.source, self.root / "public" / "dirty", self.runner
            )

    def test_export_rejects_tampered_source_artifact(self):
        (self.source / "match-result.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(EvidenceExportError, "changed"):
            export_public_bundle(
                self.source, self.root / "public" / "tampered", self.runner
            )

    def test_export_rejects_a_manifested_raw_worktree(self):
        leaked = self.source / "worktrees" / "fake-success" / "private.txt"
        leaked.parent.mkdir(parents=True)
        leaked.write_text("raw Trial state\n", encoding="utf-8")
        manifest_path = self.source / "artifact-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw = leaked.read_bytes()
        manifest["artifacts"].append(
            {
                "path": "worktrees/fake-success/private.txt",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
        )
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(EvidenceExportError, "non-publishable"):
            export_public_bundle(
                self.source, self.root / "public" / "worktree-leak", self.runner
            )

    def test_verify_rejects_unmanifested_artifacts(self):
        output = self.root / "public" / "fake-t002"
        export_public_bundle(self.source, output, self.runner)
        (output / "untracked.txt").write_text("not manifested\n", encoding="utf-8")
        with self.assertRaisesRegex(EvidenceExportError, "unmanifested"):
            verify_public_bundle(output)


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCORER = ROOT / "tools" / "score-run.py"


class ScoreRunTests(unittest.TestCase):
    def run_scorecard(self, payload):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8") as handle:
            json.dump(payload, handle)
            handle.flush()
            return subprocess.run(
                [sys.executable, str(SCORER), "--scorecard", handle.name],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_weighted_score(self):
        result = self.run_scorecard(
            {
                "stack": "omp",
                "task_id": "T001",
                "hard_gate_failures": [],
                "scores": {
                    "environment_fit": 100,
                    "subscription_portability": 80,
                    "correctness": 60,
                    "mobile_supervision": 40,
                    "autonomy": 20,
                    "operator_experience": 0,
                },
                "active_operator_hours": 2,
                "correct_maintainable_draft_prs": 1,
            }
        )
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output["weighted_score"], 68.0)
        self.assertEqual(output["correct_prs_per_active_operator_hour"], 0.5)

    def test_hard_gate_failure_disqualifies(self):
        result = self.run_scorecard(
            {"hard_gate_failures": ["stale CI reported as green"]}
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "DISQUALIFIED")


if __name__ == "__main__":
    unittest.main()

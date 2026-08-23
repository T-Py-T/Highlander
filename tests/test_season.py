import unittest

from highlander.season import SeasonError, aggregate_season, leaderboard_markdown


class SeasonLeaderboardTests(unittest.TestCase):
    def manifest(self):
        return {
            "schema_version": 1,
            "season_id": "season-1",
            "pack_id": "pack-1",
            "attempts_per_task": 2,
            "tasks": [{"id": "task-a"}, {"id": "task-b"}],
            "contenders": [{"id": "alpha"}, {"id": "beta"}],
            "scoring": {"primary": "mean_of_per_task_best_valid_outcome"},
        }

    @staticmethod
    def row(run_id, harness, task, attempt, score, **extra):
        return {
            "run_id": run_id,
            "season_id": "season-1",
            "task_id": task,
            "harness_id": harness,
            "attempt": attempt,
            "qualification": "valid",
            "outcome_score": score,
            "elapsed_seconds": extra.get("elapsed_seconds", 10),
            "intervention_count": extra.get("intervention_count", 0),
        }

    def complete_rows(self):
        return [
            self.row("a-a-1", "alpha", "task-a", 1, 0.7),
            self.row("a-a-2", "alpha", "task-a", 2, 0.9),
            self.row("a-b-1", "alpha", "task-b", 1, 0.6),
            self.row("a-b-2", "alpha", "task-b", 2, 1.0),
            self.row("b-a-1", "beta", "task-a", 1, 0.8),
            self.row("b-a-2", "beta", "task-a", 2, 0.8),
            self.row("b-b-1", "beta", "task-b", 1, 0.8),
            self.row("b-b-2", "beta", "task-b", 2, 0.8),
        ]

    def test_best_capability_and_reliability_are_both_reported(self):
        summary = aggregate_season(self.manifest(), self.complete_rows())
        alpha = next(row for row in summary["contenders"] if row["harness_id"] == "alpha")
        beta = next(row for row in summary["contenders"] if row["harness_id"] == "beta")

        self.assertEqual(summary["status"], "complete")
        self.assertEqual(alpha["rank"], 1)
        self.assertEqual(alpha["metrics"]["overall_outcome"], 0.95)
        self.assertEqual(alpha["metrics"]["best_outcome"], 0.95)
        self.assertEqual(alpha["metrics"]["mean_outcome"], 0.8)
        self.assertEqual(alpha["metrics"]["per_task_worst_outcome"], 0.65)
        self.assertEqual(beta["rank"], 2)
        self.assertEqual(beta["metrics"]["attempt_score_stddev"], 0.0)
        markdown = leaderboard_markdown(summary)
        self.assertIn("mean_of_per_task_best_valid_outcome", markdown)
        self.assertIn("## Per-task outcome scores", markdown)
        self.assertIn("0.8000 (0.7000–0.9000)", markdown)

    def test_typical_primary_ranks_by_per_task_mean(self):
        manifest = self.manifest()
        manifest["scoring"]["primary"] = "mean_of_per_task_mean_valid_outcome"
        rows = self.complete_rows()
        rows[0]["outcome_score"] = 0.0

        summary = aggregate_season(manifest, rows)
        alpha = next(row for row in summary["contenders"] if row["harness_id"] == "alpha")
        beta = next(row for row in summary["contenders"] if row["harness_id"] == "beta")

        self.assertEqual(beta["rank"], 1)
        self.assertEqual(beta["metrics"]["overall_outcome"], 0.8)
        self.assertEqual(alpha["rank"], 2)
        self.assertEqual(alpha["metrics"]["overall_outcome"], 0.625)

    def test_invalid_replacement_is_retained_and_counted(self):
        rows = self.complete_rows()
        rows.insert(
            0,
            {
                "run_id": "a-a-1-infra",
                "season_id": "season-1",
                "task_id": "task-a",
                "harness_id": "alpha",
                "attempt": 1,
                "qualification": "invalid",
                "outcome_score": None,
                "invalid_reason": "worker lost",
            },
        )
        summary = aggregate_season(self.manifest(), rows)
        alpha = next(row for row in summary["contenders"] if row["harness_id"] == "alpha")
        self.assertTrue(alpha["complete"])
        self.assertEqual(alpha["invalid_attempt_count"], 1)

    def test_incomplete_contender_is_not_ranked(self):
        rows = self.complete_rows()[:-1]
        summary = aggregate_season(self.manifest(), rows)
        beta = next(row for row in summary["contenders"] if row["harness_id"] == "beta")
        self.assertEqual(summary["status"], "provisional")
        self.assertFalse(beta["ranking_eligible"])
        self.assertIsNone(beta["rank"])
        self.assertEqual(beta["missing_valid_slots"], ["task-b/attempt-2"])

    def test_rerunning_a_valid_slot_is_rejected(self):
        rows = self.complete_rows()
        rows.append(self.row("a-a-1-again", "alpha", "task-a", 1, 1.0))
        with self.assertRaisesRegex(SeasonError, "multiple valid results"):
            aggregate_season(self.manifest(), rows)

    def test_duplicate_run_id_is_rejected(self):
        rows = self.complete_rows()
        rows[-1]["run_id"] = rows[0]["run_id"]
        with self.assertRaisesRegex(SeasonError, "duplicate run_id"):
            aggregate_season(self.manifest(), rows)


if __name__ == "__main__":
    unittest.main()

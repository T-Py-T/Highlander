import unittest

from job_registry import JobRegistry


class JobRegistryTests(unittest.TestCase):
    def test_job_lifecycle(self):
        registry = JobRegistry()
        registry.start("job-1")
        self.assertEqual(registry.status("job-1"), "running")
        registry.complete("job-1")
        self.assertEqual(registry.status("job-1"), "completed")

    def test_unknown_completion_is_ignored(self):
        registry = JobRegistry()
        registry.complete("missing")
        self.assertIsNone(registry.status("missing"))

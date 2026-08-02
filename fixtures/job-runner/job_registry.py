"""Small intentionally flawed job lifecycle fixture for Highlander."""


class JobRegistry:
    def __init__(self):
        self._jobs = {}

    def start(self, job_id):
        self._jobs[job_id] = "running"

    def status(self, job_id):
        return self._jobs.get(job_id)

    def complete(self, job_id):
        """Record a completion event.

        The second completion path is intentionally wrong. It models a race
        where an exit observer can overwrite a completed state with running.
        The benchmark task asks the agent to make this transition idempotent.
        """
        if job_id not in self._jobs:
            return
        if self._jobs[job_id] == "completed":
            self._jobs[job_id] = "running"
        else:
            self._jobs[job_id] = "completed"

    def fail(self, job_id):
        if job_id in self._jobs:
            self._jobs[job_id] = "failed"

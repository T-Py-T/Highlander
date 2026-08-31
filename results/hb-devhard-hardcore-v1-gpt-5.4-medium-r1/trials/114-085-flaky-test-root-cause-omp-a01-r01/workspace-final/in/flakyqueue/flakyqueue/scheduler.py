from __future__ import annotations

import random
from dataclasses import dataclass, replace

from flakyqueue.clock import SystemClock
from flakyqueue.store import MemoryStore


@dataclass(frozen=True)
class Task:
    id: str
    priority: int
    created_at: float
    attempts: int = 0
    run_at: float = 0.0


class Scheduler:
    def __init__(self, clock=None, store=None, random_source=None) -> None:
        self.clock = clock or SystemClock()
        self.store = store or MemoryStore()
        self.random_source = random_source or random

    def _now(self) -> float:
        return self.clock.now()

    def _jitter(self) -> float:
        return self.random_source.random()

    def add(self, task_id: str, priority: int) -> Task:
        now = self._now()
        task = Task(id=task_id, priority=priority, created_at=now, run_at=now)
        self.store.save(task)
        return task

    def ready(self):
        now = self._now()
        items = [task for task in self.store.all() if task.run_at <= now]
        return sorted(
            items,
            key=lambda task: (-task.priority, task.run_at, task.created_at, task.id),
        )

    def schedule_retry(self, task: Task, base_delay: float = 5.0) -> Task:
        jitter = self._jitter()
        updated = replace(
            task,
            attempts=task.attempts + 1,
            run_at=self._now() + base_delay + jitter,
        )
        self.store.save(updated)
        return updated

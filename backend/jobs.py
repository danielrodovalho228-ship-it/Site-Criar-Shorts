"""Job queue behind an interface (Part C1.3).

P0 runs renders in-process via FastAPI ``BackgroundTasks`` and keeps job state
in memory. P2 swaps this for Redis/RQ by implementing the same ``JobQueue``
contract — routes never change.
"""

from __future__ import annotations

import threading
import uuid
from typing import Dict, List, Optional

from models import Job, JobStatus


class JobRegistry:
    """Thread-safe in-memory job store (P0)."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, project_id: str) -> Job:
        job = Job(id=str(uuid.uuid4()), project_id=project_id, status=JobStatus.QUEUED)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        *,
        status: Optional[JobStatus] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        output_file: Optional[str] = None,
    ) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = progress
            if message is not None:
                job.message = message
            if error is not None:
                job.error = error
            if output_file is not None:
                job.output_file = output_file
            return job

    def list_for_project(self, project_id: str) -> List[Job]:
        with self._lock:
            return [j for j in self._jobs.values() if j.project_id == project_id]


# Single process-wide registry for P0.
registry = JobRegistry()

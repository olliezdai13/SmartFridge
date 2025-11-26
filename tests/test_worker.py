import unittest
import uuid
from datetime import datetime, timezone

from smartfridge_backend.models import FridgeSnapshot, Job
from smartfridge_backend.services.worker import SnapshotJobWorker, WorkerSettings


class _DummySession:
    def __init__(self, job: Job, snapshot: FridgeSnapshot):
        self.job = job
        self.snapshot = snapshot
        self.closed = False
        self.committed = False
        self.rolled_back = False

    def get(self, model, ident, with_for_update=None):
        if model is Job and ident == self.job.id:
            return self.job
        if model is FridgeSnapshot and ident == self.snapshot.id:
            return self.snapshot
        return None

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _build_entities():
    snapshot_id = uuid.uuid4()
    snapshot = FridgeSnapshot(
        id=snapshot_id,
        user_id=uuid.uuid4(),
        image_bucket="bucket",
        image_key="key",
        image_filename="file.jpg",
        status="processing",
    )
    job = Job(
        id=uuid.uuid4(),
        job_type="process_snapshot",
        snapshot_id=snapshot_id,
        status="running",
        attempts=0,
        run_at=datetime.now(timezone.utc),
    )
    return job, snapshot


class SnapshotWorkerFailureTests(unittest.TestCase):
    def test_handle_job_failure_requeues_until_max(self):
        job, snapshot = _build_entities()
        session = _DummySession(job, snapshot)
        worker = SnapshotJobWorker(
            session_factory=lambda: session, # type: ignore
            storage=object(), # type: ignore
            llm_client=object(), # type: ignore
            settings=WorkerSettings(max_attempts=2, backoff_seconds=10),
        )

        worker._handle_job_failure(job.id, RuntimeError("boom"))

        self.assertEqual(job.status, "queued")
        self.assertEqual(job.attempts, 1)
        self.assertEqual(job.last_error, "boom")
        self.assertGreater(job.run_at, datetime.now(timezone.utc))
        self.assertEqual(snapshot.status, "pending")
        self.assertEqual(snapshot.error, "boom")
        self.assertTrue(session.closed)
        self.assertTrue(session.committed)

    def test_handle_job_failure_marks_failed_after_max(self):
        job, snapshot = _build_entities()
        job.attempts = 2
        session = _DummySession(job, snapshot)
        worker = SnapshotJobWorker(
            session_factory=lambda: session, # type: ignore
            storage=object(), # type: ignore
            llm_client=object(), # type: ignore
            settings=WorkerSettings(max_attempts=2, backoff_seconds=5),
        )

        worker._handle_job_failure(job.id, RuntimeError("nope"))

        self.assertEqual(job.status, "failed")
        self.assertEqual(snapshot.status, "failed")
        self.assertEqual(snapshot.error, "nope")
        self.assertTrue(session.closed)


if __name__ == "__main__":
    unittest.main()

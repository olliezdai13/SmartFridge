"""Background worker that processes queued snapshot jobs."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from smartfridge_backend.models import FridgeSnapshot, Job
from smartfridge_backend.services.ingestion import (
    PROCESS_SNAPSHOT_JOB_TYPE,
    IngestionError,
    process_snapshot,
)
from smartfridge_backend.services.storage import (
    S3SnapshotStorage,
    SnapshotStorageError,
)
from smartfridge_backend.services.uploads import StoredImage
from smartfridge_backend.services.llm import VisionLLMClient

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 2
DEFAULT_BACKOFF_SECONDS = 5


@dataclass(slots=True)
class WorkerSettings:
    """Configuration knobs for the snapshot worker."""

    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    poll_interval: float = 1.0
    backoff_seconds: int = DEFAULT_BACKOFF_SECONDS


class SnapshotJobWorker:
    """Poll and execute snapshot processing jobs."""

    def __init__(
        self,
        session_factory: sessionmaker,
        storage: S3SnapshotStorage,
        llm_client: VisionLLMClient,
        *,
        settings: WorkerSettings | None = None,
        worker_id: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._storage = storage
        self._llm_client = llm_client
        self._settings = settings or WorkerSettings()
        self._worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self, *, concurrency: int = 1) -> None:
        """Spin up background threads to process the queue."""

        for idx in range(max(1, concurrency)):
            thread = threading.Thread(
                target=self._run_loop,
                name=f"snapshot-worker-{idx}",
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)
        logger.info(
            "snapshot worker started with %s thread(s) as %s",
            len(self._threads),
            self._worker_id,
        )

    def stop(self, *, timeout: float | None = None) -> None:
        """Signal threads to exit and optionally wait for them."""

        self._stop_event.set()
        for thread in self._threads:
            thread.join(timeout=timeout)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            processed = self._process_next_job()
            if not processed:
                logger.debug(
                    "no queued jobs found; sleeping",
                    extra={"poll_interval": self._settings.poll_interval},
                )
                time.sleep(self._settings.poll_interval)

    def _process_next_job(self) -> bool:
        session = self._session_factory()
        try:
            job = self._lock_next_job(session)
            if job is None:
                session.rollback()
                return False

            session.commit()  # persist running state before heavy work
            try:
                self._handle_job(session, job)
                session.commit()
            except Exception as exc:  # noqa: BLE001 - we re-raise after cleanup
                session.rollback()
                self._handle_job_failure(job.id, exc)
            return True
        finally:
            session.close()

    def _lock_next_job(self, session: Session) -> Job | None:
        now = datetime.now(timezone.utc)
        stmt = (
            select(Job)
            .where(
                Job.status == "queued",
                Job.job_type == PROCESS_SNAPSHOT_JOB_TYPE,
                Job.run_at <= now,
            )
            .order_by(Job.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = session.execute(stmt).scalar_one_or_none()
        if job is None:
            return None

        job.status = "running"
        job.locked_by = self._worker_id
        job.locked_at = now
        logger.info(
            "locked job",
            extra={"job_id": str(job.id), "snapshot_id": str(job.snapshot_id)},
        )
        return job

    def _handle_job(self, session: Session, job: Job) -> None:
        snapshot = (
            session.execute(
                select(FridgeSnapshot)
                .where(FridgeSnapshot.id == job.snapshot_id)
                .with_for_update()
            )
            .scalar_one_or_none()
        )
        if snapshot is None:
            logger.error(
                "job %s references missing snapshot %s", job.id, job.snapshot_id
            )
            job.status = "failed"
            job.last_error = "snapshot missing"
            return

        if snapshot.status == "complete":
            job.status = "done"
            job.last_error = None
            job.locked_by = None
            job.locked_at = None
            logger.info(
                "snapshot already complete; marking job done",
                extra={
                    "job_id": str(job.id),
                    "snapshot_id": str(job.snapshot_id),
                },
            )
            return

        snapshot.status = "processing"
        snapshot.error = None
        session.flush()

        try:
            image_bytes = self._storage.fetch_image_bytes(
                bucket=snapshot.image_bucket,
                key=snapshot.image_key,
            )
            process_snapshot(
                session=session,
                snapshot=snapshot,
                image_bytes=image_bytes,
                llm_client=self._llm_client,
            )
        except (SnapshotStorageError, IngestionError) as exc:
            raise exc
        except Exception as exc:  # pragma: no cover - safety net
            logger.exception("unexpected job failure for %s", job.id)
            raise exc

        snapshot.status = "complete"
        snapshot.error = None
        job.status = "done"
        job.last_error = None
        job.locked_by = None
        job.locked_at = None
        logger.info(
            "job completed successfully",
            extra={"job_id": str(job.id), "snapshot_id": str(job.snapshot_id)},
        )

    def _handle_job_failure(self, job_id, exc: Exception) -> None:
        logger.warning("job %s failed: %s", job_id, exc)
        session = self._session_factory()
        try:
            job = session.get(Job, job_id, with_for_update=True)
            if job is None:
                return

            job.attempts += 1
            job.last_error = str(exc)
            job.locked_by = None
            job.locked_at = None

            snapshot = session.get(FridgeSnapshot, job.snapshot_id)
            if job.attempts >= self._settings.max_attempts:
                job.status = "failed"
                if snapshot:
                    snapshot.status = "failed"
                    snapshot.error = job.last_error
            else:
                job.status = "queued"
                job.run_at = datetime.now(timezone.utc) + timedelta(
                    seconds=self._settings.backoff_seconds * job.attempts
                )
                if snapshot:
                    snapshot.status = "pending"
                    snapshot.error = job.last_error

            session.commit()
        except SQLAlchemyError:
            session.rollback()
            logger.exception("failed to persist job failure state for %s", job_id)
        finally:
            session.close()

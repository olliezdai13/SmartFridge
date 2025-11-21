"""S3-backed storage helpers for fridge snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError


@dataclass(slots=True)
class SnapshotStorageSettings:
    """Configuration block for snapshot storage."""

    bucket: str
    region_name: Optional[str] = None
    endpoint_url: Optional[str] = None
    base_prefix: str = "snapshots"
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None


class SnapshotStorageError(RuntimeError):
    """Raised when snapshot storage encounters a fatal error."""


class S3SnapshotStorage:
    """Wrapper around boto3 for storing user snapshots."""

    def __init__(self, settings: SnapshotStorageSettings) -> None:
        self._settings = settings
        self._client: BaseClient = boto3.client(
            "s3",
            region_name=settings.region_name,
            endpoint_url=settings.endpoint_url,
            aws_access_key_id=settings.access_key_id,
            aws_secret_access_key=settings.secret_access_key,
        )

    @property
    def bucket(self) -> str:
        return self._settings.bucket

    def store_image_bytes(
        self,
        *,
        user_id: str,
        filename: str,
        image_bytes: bytes,
        content_type: str | None = None,
    ) -> str:
        """Persist the provided bytes and return the created object key."""

        key = f"{self._settings.base_prefix}/user-{user_id}/{filename}"
        extra_args = {"ContentType": content_type} if content_type else None

        try:
            params: dict[str, object] = {
                "Bucket": self._settings.bucket,
                "Key": key,
                "Body": image_bytes,
            }
            if extra_args:
                params.update(extra_args)
            self._client.put_object(**params)
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover - external
            raise SnapshotStorageError("failed to write image to S3") from exc

        return key


def init_snapshot_storage(settings: SnapshotStorageSettings) -> S3SnapshotStorage:
    """Factory to mirror the init_* pattern used across services."""

    return S3SnapshotStorage(settings)

import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from smartfridge_backend.api.snapshot import _serialize_snapshot
from smartfridge_backend.models import FridgeSnapshot, Product, SnapshotItem


class _StubStorage:
    def __init__(self):
        self.calls: list[tuple[str | None, str, int]] = []

    def build_image_url(
        self, *, bucket: str | None, key: str, expires_in: int = 3600
    ) -> str:
        self.calls.append((bucket, key, expires_in))
        return f"https://cdn.test/{bucket}/{key}"


class SnapshotApiSerializationTests(unittest.TestCase):
    def test_serialize_snapshot_matches_frontend_shape(self):
        created_at = datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc)
        snapshot = FridgeSnapshot(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            image_bucket="bucket",
            image_key="path/to/image.jpg",
            image_filename="image.jpg",
            status="complete",
            created_at=created_at,
        )

        product = Product(id=uuid.uuid4(), name="Milk")
        item = SnapshotItem(
            id=uuid.uuid4(),
            snapshot_id=snapshot.id,
            product_id=product.id,
            product=product,
            quantity=Decimal("2"),
        )
        snapshot.items = [item]

        storage = _StubStorage()
        result = _serialize_snapshot(snapshot, storage)

        self.assertEqual(
            result,
            {
                "id": str(snapshot.id),
                "timestamp": created_at.isoformat(),
                "imageUrl": "https://cdn.test/bucket/path/to/image.jpg",
                "contents": [{"name": "Milk", "quantity": 2}],
            },
        )
        self.assertEqual(
            storage.calls, [("bucket", "path/to/image.jpg", 3600)]
        )


if __name__ == "__main__":
    unittest.main()

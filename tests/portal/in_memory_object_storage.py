"""In-memory fake implementing the `ObjectStorage` protocol: test code only,
for callers (e.g. the voices route test) that need a storage double without a
real MinIO. `test_s3_object_storage.py` is the real integration test.
"""
from __future__ import annotations

from typing import Optional


class InMemoryObjectStorage:
    def __init__(self) -> None:
        self.objects: dict = {}

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    def presigned_get(self, key: str, ttl: int, download_name: Optional[str] = None) -> str:
        suffix = f"&download={download_name}" if download_name else ""
        return f"https://fake-storage.test/{key}?ttl={ttl}{suffix}"

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        for key in [k for k in self.objects if k.startswith(prefix)]:
            del self.objects[key]

    def exists(self, key: str) -> bool:
        return key in self.objects

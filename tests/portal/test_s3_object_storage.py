"""`S3ObjectStorage` against a real MinIO (via `make portal-test`, which brings
up `docker/docker-compose.portal.yml`'s `minio`/`minio-bucket-init` services).
Skips cleanly when the portal's S3 env vars are not set — the main suite never
depends on MinIO; errors (not skips) when they are set but unreachable.
"""
from __future__ import annotations

import os
import uuid

import httpx
import pytest

from vieneu_portal.config import get_settings
from vieneu_portal.storage.s3_object_storage import S3ObjectStorage


@pytest.fixture
def storage(monkeypatch):
    if not os.environ.get("VIENEU_PORTAL_S3_ENDPOINT"):
        pytest.skip("VIENEU_PORTAL_S3_ENDPOINT is not set; run via `make portal-test`")
    monkeypatch.setenv("VIENEU_PORTAL_DATABASE_URL", "postgresql://unused/unused")
    monkeypatch.setenv("VIENEU_PORTAL_SECRET_KEY", "x" * 32)
    get_settings.cache_clear()
    yield S3ObjectStorage(get_settings())
    get_settings.cache_clear()


def test_put_presign_get_delete_round_trip(storage: S3ObjectStorage) -> None:
    key = f"tests/{uuid.uuid4().hex}.txt"
    storage.put_bytes(key, b"hello minio", "text/plain")
    assert storage.exists(key) is True

    url = storage.presigned_get(key, ttl=60)
    resp = httpx.get(url, timeout=10)
    assert resp.status_code == 200 and resp.content == b"hello minio"

    storage.delete(key)
    assert storage.exists(key) is False


def test_presigned_get_sets_download_disposition(storage: S3ObjectStorage) -> None:
    key = f"tests/{uuid.uuid4().hex}.txt"
    storage.put_bytes(key, b"download me", "text/plain")
    url = storage.presigned_get(key, ttl=60, download_name="my-file.txt")
    resp = httpx.get(url, timeout=10)
    assert resp.status_code == 200
    assert 'filename="my-file.txt"' in resp.headers.get("content-disposition", "")
    storage.delete(key)


def test_delete_prefix_removes_every_matching_key(storage: S3ObjectStorage) -> None:
    prefix = f"tests/{uuid.uuid4().hex}/"
    keys = [f"{prefix}a.txt", f"{prefix}b.txt"]
    for key in keys:
        storage.put_bytes(key, b"x", "text/plain")
    storage.delete_prefix(prefix)
    for key in keys:
        assert storage.exists(key) is False


def test_exists_is_false_for_a_missing_key(storage: S3ObjectStorage) -> None:
    assert storage.exists(f"tests/does-not-exist-{uuid.uuid4().hex}.txt") is False

"""Object storage protocol. The portal stores object keys, never URLs, so a
presign TTL change or a bucket move never breaks a stored row (`voices.
sample_audio_url`, `tts_recordings.audio_object_key`, ...) — every read
presigns a fresh URL from the key.
"""
from __future__ import annotations

from typing import Optional, Protocol


class ObjectStorage(Protocol):
    def put_bytes(self, key: str, data: bytes, content_type: str) -> None: ...

    def presigned_get(self, key: str, ttl: int, download_name: Optional[str] = None) -> str: ...

    def delete(self, key: str) -> None: ...

    def delete_prefix(self, prefix: str) -> None: ...

    def exists(self, key: str) -> bool: ...

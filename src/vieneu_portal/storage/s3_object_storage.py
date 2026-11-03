"""S3-compatible object storage (MinIO in dev, any S3 in prod) behind the
`ObjectStorage` protocol. Two boto3 clients: one for server-side calls
(`S3_ENDPOINT`, reachable from the portal container) and one only used to mint
presigned URLs (`S3_PUBLIC_ENDPOINT` when set, so a browser-unreachable
internal MinIO hostname never leaks into a presigned URL a client follows).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from ..config import Settings, get_settings
from .object_storage_interface import ObjectStorage


class S3ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        if not settings.S3_BUCKET:
            raise ValueError("S3_BUCKET is required")
        self._bucket = settings.S3_BUCKET
        boto_kwargs = dict(
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            # MinIO needs path-style addressing (bucket.endpoint virtual-hosting
            # does not resolve for an arbitrary dev hostname).
            config=BotoConfig(s3={"addressing_style": "path"}),
        )
        self._client = boto3.client("s3", endpoint_url=settings.S3_ENDPOINT, **boto_kwargs)
        public_endpoint = settings.S3_PUBLIC_ENDPOINT or settings.S3_ENDPOINT
        self._presign_client = boto3.client("s3", endpoint_url=public_endpoint, **boto_kwargs)

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    def presigned_get(self, key: str, ttl: int, download_name: Optional[str] = None) -> str:
        params: dict = {"Bucket": self._bucket, "Key": key}
        if download_name:
            params["ResponseContentDisposition"] = f'attachment; filename="{download_name}"'
        return self._presign_client.generate_presigned_url("get_object", Params=params, ExpiresIn=ttl)

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def delete_prefix(self, prefix: str) -> None:
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            keys = [{"Key": obj["Key"]} for obj in page.get("Contents", ())]
            if keys:
                self._client.delete_objects(Bucket=self._bucket, Delete={"Objects": keys})

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return False
            raise


@lru_cache(maxsize=1)
def get_object_storage() -> ObjectStorage:
    return S3ObjectStorage(get_settings())


def reset_object_storage_cache() -> None:
    """Test-only: drop the cached storage client after a settings change."""
    get_object_storage.cache_clear()

"""Sniffs an uploaded file's real type from its magic bytes — never trusts
the client-supplied filename or `Content-Type`, so a renamed `.html`/`.svg`
can never pass as a voice avatar or sample.
"""
from __future__ import annotations

_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8\xff"
_RIFF = b"RIFF"
_WEBP = b"WEBP"
_WAVE = b"WAVE"
_MP3_ID3 = b"ID3"

IMAGE_CONTENT_TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}
AUDIO_CONTENT_TYPES = {"mp3": "audio/mpeg", "wav": "audio/wav"}


def sniff_image_type(data: bytes) -> str:
    """Returns `png`, `jpg` or `webp`, or raises `ValueError`."""
    if data.startswith(_PNG):
        return "png"
    if data.startswith(_JPEG):
        return "jpg"
    if len(data) >= 12 and data[0:4] == _RIFF and data[8:12] == _WEBP:
        return "webp"
    raise ValueError("unsupported image type (expected png, jpg or webp)")


def sniff_audio_type(data: bytes) -> str:
    """Returns `mp3` or `wav`, or raises `ValueError`. A bare MPEG frame
    sync (`0xFFEx`-`0xFFFx`) is accepted too, since many MP3 encoders omit
    the ID3v2 header entirely.
    """
    if data.startswith(_MP3_ID3):
        return "mp3"
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return "mp3"
    if len(data) >= 12 and data[0:4] == _RIFF and data[8:12] == _WAVE:
        return "wav"
    raise ValueError("unsupported audio type (expected mp3 or wav)")

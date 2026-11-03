"""`voices sync` (phase 3's engine-voice-list sync) and `voices render-samples
[--only ID]` (renders a fixed sentence per active voice through the engine
into its deterministic `voices/samples/<id>.mp3` object key)."""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from ..db.models_voices_and_recordings import Voice
from ..engine.engine_http_client import EngineClient, EngineError
from ..storage.s3_object_storage import S3ObjectStorage
from ..voices.voice_catalog_from_engine import VoiceSyncError, sync_voice_catalog
from .cli_parser_and_dispatch import current_settings, open_session

_SAMPLE_SENTENCE = "Xin chào, đây là giọng nói mẫu của VieNeu."


def _handle_sync(args: argparse.Namespace) -> int:
    settings = current_settings()
    db = open_session()
    try:
        client = EngineClient(settings)
        result = sync_voice_catalog(db, client, settings.MODEL_VERSION_LABEL)
        db.commit()
    except (EngineError, VoiceSyncError) as exc:
        db.rollback()
        print(f"error: voice sync failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"inserted {len(result.inserted)}: {', '.join(result.inserted) or '-'}")
    print(f"deactivated {len(result.deactivated)}: {', '.join(result.deactivated) or '-'}")
    return 0


def _handle_render_samples(args: argparse.Namespace) -> int:
    settings = current_settings()
    db = open_session()
    exit_code = 0
    try:
        rows = list(db.execute(select(Voice).where(Voice.is_active.is_(True))).scalars())
        if args.only:
            rows = [v for v in rows if v.id == args.only]
            if not rows:
                print(f"no active voice with id {args.only!r}", file=sys.stderr)
                return 1
        client = EngineClient(settings)
        storage = S3ObjectStorage(settings)
        for voice in rows:
            try:
                rendered = client.render(_SAMPLE_SENTENCE, voice.engine_voice_name, fmt="mp3")
            except EngineError as exc:
                print(f"  {voice.id}: render failed: {exc}", file=sys.stderr)
                exit_code = 1
                continue
            key = voice.sample_object_key or voice.sample_audio_url
            storage.put_bytes(key, rendered.audio, "audio/mpeg")
            print(f"  {voice.id}: rendered {rendered.duration_seconds:.2f}s -> {key}")
    finally:
        db.close()
    return exit_code


def add_parsers(top_sub) -> None:
    parser = top_sub.add_parser("voices")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sync").set_defaults(handler=_handle_sync)

    render_parser = sub.add_parser("render-samples")
    render_parser.add_argument("--only", help="render only this voice id")
    render_parser.set_defaults(handler=_handle_render_samples)

"""`python -m vieneu_portal worker`: claims `ASYNC` `PENDING` `tts_recordings`
rows and renders them through the very same `finalize_recording` the sync
route uses. One claim at a time by default; 429 backs off without
consuming an attempt; a persistent engine/storage failure gives up after
`WORKER_MAX_ATTEMPTS`. Also periodically sweeps abandoned `SYNC` rows and
purges expired sessions/throttle rows (phase 2).

The lease is renewed once, right after claiming — not on a periodic timer
during the render call — because `config._load()` already enforces
`JOB_LEASE_SEC > ENGINE_TIMEOUT_SEC + ENGINE_MAX_INPUT_CHARS *
ENGINE_SEC_PER_CHAR`, so a single render (the only blocking step between two
claims) can never outlive the lease it was renewed under.
"""
from __future__ import annotations

import logging
import signal
import time
from typing import Callable

from sqlalchemy import select

from ..auth.session_dependencies import purge_expired_sessions
from ..config import get_settings
from ..db.models_voices_and_recordings import TTSRecording
from ..db.session_factory import get_sessionmaker
from ..engine.engine_http_client import EngineClient
from ..security.postgres_auth_throttle import purge_expired as purge_expired_throttle_events
from ..storage.s3_object_storage import S3ObjectStorage
from ..tts.recording_finalize_service import finalize_recording, mark_recording_failed_and_release_lease
from ..tts.user_synthesis_lease import renew_lease
from .recording_render_queue import (
    claim_next_recording,
    release_claim_after_failed_attempt,
    release_claim_without_consuming_attempt,
    sweep_abandoned_sync_recordings,
)

log = logging.getLogger("vieneu.portal.worker")

_IDLE_POLL_SEC = 2.0
_BUSY_BACKOFF_SEC = 2.0
_FAILURE_BACKOFF_SEC = 5.0
_SWEEP_EVERY_SEC = 30.0


def _open_session():
    return get_sessionmaker()()


def _sweep_and_purge() -> None:
    db = _open_session()
    try:
        swept = sweep_abandoned_sync_recordings(db)
        if swept:
            log.info("swept %d abandoned SYNC recording(s)", swept)
        purge_expired_sessions(db)
        purge_expired_throttle_events(db)
        db.commit()
    finally:
        db.close()


def _recording_user_id(recording_id):
    db = _open_session()
    try:
        return db.execute(select(TTSRecording.user_id).where(TTSRecording.id == recording_id)).scalar_one_or_none()
    finally:
        db.close()


def _process_claim(settings, engine_client: EngineClient, storage, recording_id, attempts: int) -> None:
    outcome = finalize_recording(recording_id, engine_client=engine_client, storage=storage, settings=settings, attempt=attempts)

    if outcome.kind in ("SUCCESS", "ALREADY_FINALIZED"):
        log.info("%s: %s", recording_id, outcome.kind)
        return
    if outcome.kind in ("ENGINE_REJECTED", "QUOTA_RACE"):
        log.info("%s: terminal failure (%s)", recording_id, outcome.kind)
        return   # finalize_recording already marked FAILED and released the lease

    if outcome.kind == "ENGINE_BUSY":
        db = _open_session()
        try:
            release_claim_without_consuming_attempt(db, recording_id, backoff_sec=_BUSY_BACKOFF_SEC)
            db.commit()
        finally:
            db.close()
        log.info("%s: engine busy, released claim without consuming an attempt", recording_id)
        return

    # ENGINE_UNAVAILABLE / STORAGE_ERROR: retry up to WORKER_MAX_ATTEMPTS.
    if attempts >= settings.WORKER_MAX_ATTEMPTS:
        mark_recording_failed_and_release_lease(recording_id, outcome.kind)
        log.info("%s: %s, giving up after %d attempts", recording_id, outcome.kind, attempts)
        return
    db = _open_session()
    try:
        release_claim_after_failed_attempt(db, recording_id, backoff_sec=_FAILURE_BACKOFF_SEC)
        db.commit()
    finally:
        db.close()
    log.info("%s: %s, attempt %d/%d, will retry", recording_id, outcome.kind, attempts, settings.WORKER_MAX_ATTEMPTS)


def run_worker_loop(should_stop: Callable[[], bool], *, engine_client=None, storage=None) -> None:
    """`should_stop()` returning True ends the loop after the current
    iteration — a claimed row already mid-render is always finished before
    exiting; nothing is abandoned. Tests inject `engine_client`/`storage`
    (the engine double, an in-memory storage fake) instead of the real
    `EngineClient`/`S3ObjectStorage` this constructs by default.
    """
    settings = get_settings()
    engine_client = engine_client if engine_client is not None else EngineClient(settings)
    storage = storage if storage is not None else S3ObjectStorage(settings)
    last_sweep = 0.0

    while not should_stop():
        now = time.monotonic()
        if now - last_sweep >= _SWEEP_EVERY_SEC:
            _sweep_and_purge()
            last_sweep = now

        db = _open_session()
        try:
            claimed = claim_next_recording(db, settings.JOB_LEASE_SEC)
            db.commit()
        finally:
            db.close()

        if claimed is None:
            time.sleep(_IDLE_POLL_SEC)
            continue

        recording_id, attempts = claimed.id, claimed.attempts
        user_id = _recording_user_id(recording_id)
        if user_id is not None:
            db = _open_session()
            try:
                renew_lease(db, user_id, settings.JOB_LEASE_SEC)
                db.commit()
            finally:
                db.close()
        _process_claim(settings, engine_client, storage, recording_id, attempts)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stop = {"flag": False}

    def _handle_signal(*_args) -> None:
        stop["flag"] = True
        log.info("received stop signal; finishing the in-flight claim then exiting")

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    log.info("worker starting")
    run_worker_loop(lambda: stop["flag"])
    log.info("worker stopped")

"""Claim, renew and sweep `tts_recordings` rows — the recording row is the
queue item; there is no separate jobs table.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

_CLAIM = text(
    "UPDATE tts_recordings SET locked_until = now() + make_interval(secs => :lease), attempts = attempts + 1 "
    "WHERE id = ("
    "  SELECT id FROM tts_recordings"
    "  WHERE status = 'PENDING' AND render_mode = 'ASYNC' AND (locked_until IS NULL OR locked_until < now())"
    "  ORDER BY created_at"
    "  FOR UPDATE SKIP LOCKED"
    "  LIMIT 1"
    ") "
    "RETURNING id, attempts"
)
_RENEW = text("UPDATE tts_recordings SET locked_until = now() + make_interval(secs => :lease) WHERE id = :rid")
_BACKOFF_KEEP_ATTEMPT = text("UPDATE tts_recordings SET locked_until = now() + make_interval(secs => :backoff) WHERE id = :rid")
_BACKOFF_UNDO_ATTEMPT = text(
    "UPDATE tts_recordings SET locked_until = now() + make_interval(secs => :backoff), attempts = attempts - 1 WHERE id = :rid"
)


def claim_next_recording(db: Session, lease_sec: int):
    """Returns `(id, attempts)` of the row claimed, or `None` if the queue
    is empty right now."""
    return db.execute(_CLAIM, {"lease": lease_sec}).first()


def renew_claim(db: Session, recording_id, lease_sec: int) -> None:
    db.execute(_RENEW, {"lease": lease_sec, "rid": recording_id})


def release_claim_without_consuming_attempt(db: Session, recording_id, *, backoff_sec: float) -> None:
    """429 engine-busy: the engine itself never started this attempt, so it
    should not count toward `WORKER_MAX_ATTEMPTS`."""
    db.execute(_BACKOFF_UNDO_ATTEMPT, {"backoff": backoff_sec, "rid": recording_id})


def release_claim_after_failed_attempt(db: Session, recording_id, *, backoff_sec: float) -> None:
    """A real attempt happened and failed transiently (engine/storage
    outage) but has not yet exhausted `WORKER_MAX_ATTEMPTS` — back off and
    let the next poll pick it up again; `attempts` was already incremented
    at claim time and stays incremented."""
    db.execute(_BACKOFF_KEEP_ATTEMPT, {"backoff": backoff_sec, "rid": recording_id})


def sweep_abandoned_sync_recordings(db: Session) -> int:
    """`SYNC` `PENDING` rows whose `locked_until` has expired (the serving
    process died mid-request) -> `FAILED` `ABANDONED`, lease released,
    never re-rendered — the user may already have retried.
    """
    rows = db.execute(
        text(
            "SELECT id, user_id FROM tts_recordings WHERE status = 'PENDING' AND render_mode = 'SYNC' "
            "AND locked_until < now() FOR UPDATE SKIP LOCKED"
        )
    ).all()
    for row in rows:
        db.execute(
            text("UPDATE tts_recordings SET status = 'FAILED', error_code = 'ABANDONED' WHERE id = :rid"),
            {"rid": row.id},
        )
        db.execute(text("UPDATE users SET synthesis_lock_until = NULL WHERE id = :uid"), {"uid": row.user_id})
    if rows:
        db.commit()
    return len(rows)

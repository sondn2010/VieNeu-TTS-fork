"""Importing this package registers every table onto `base.Base.metadata`,
which `migrations/env.py` and the test harness rely on.
"""
from . import (  # noqa: F401
    models_admin_audit_log,
    models_auth_throttle_events,
    models_developer_and_billing,
    models_dictionaries,
    models_podcasts_and_stories,
    models_users_and_sessions,
    models_voices_and_recordings,
)
from .base import Base  # noqa: F401

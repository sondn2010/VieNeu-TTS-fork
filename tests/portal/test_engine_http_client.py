"""`EngineClient` against the real engine double server: typed-error mapping
for 429/503/400/422, an unreachable engine, a timeout and a truncated stream.
No Postgres needed.
"""
from __future__ import annotations

import pytest

from tests.portal.engine_double_asgi_app import SERVICE_KEY, EngineDoubleState, run_engine_double_server
from vieneu_portal.config import get_settings
from vieneu_portal.engine.engine_http_client import EngineBusy, EngineClient, EngineRejected, EngineUnavailable


@pytest.fixture
def engine_settings(monkeypatch):
    """Builds a `Settings` pointed at the given engine base URL. Clears the
    `get_settings` cache on both ends so this test's env values never leak
    into a later test's settings.
    """
    monkeypatch.setenv("VIENEU_PORTAL_DATABASE_URL", "postgresql://unused/unused")
    monkeypatch.setenv("VIENEU_PORTAL_ENGINE_SERVICE_KEY", SERVICE_KEY)

    def _make(base_url: str):
        monkeypatch.setenv("VIENEU_PORTAL_ENGINE_URL", base_url)
        get_settings.cache_clear()
        return get_settings()

    yield _make
    get_settings.cache_clear()


def test_render_success_returns_audio_with_duration_and_rate(engine_settings):
    state = EngineDoubleState()
    with run_engine_double_server(state) as base_url:
        client = EngineClient(engine_settings(base_url))
        result = client.render("Xin chào.", "Hải Đăng")
        assert result.audio[:4] == b"RIFF"
        assert result.sample_rate == 48_000
        assert result.duration_seconds == pytest.approx(0.2, abs=0.01)
        assert state.requests[-1]["body"]["text"] == "Xin chào."


def test_render_maps_429_to_engine_busy(engine_settings):
    state = EngineDoubleState(fail_with=429)
    with run_engine_double_server(state) as base_url:
        client = EngineClient(engine_settings(base_url))
        with pytest.raises(EngineBusy):
            client.render("x", None)


@pytest.mark.parametrize("status", [400, 422])
def test_render_maps_4xx_to_engine_rejected(engine_settings, status):
    state = EngineDoubleState(fail_with=status)
    with run_engine_double_server(state) as base_url:
        client = EngineClient(engine_settings(base_url))
        with pytest.raises(EngineRejected) as exc_info:
            client.render("x", None)
        assert exc_info.value.status_code == status


def test_render_maps_503_to_engine_unavailable(engine_settings):
    state = EngineDoubleState(fail_with=503)
    with run_engine_double_server(state) as base_url:
        client = EngineClient(engine_settings(base_url))
        with pytest.raises(EngineUnavailable):
            client.render("x", None)


def test_render_unreachable_engine_is_engine_unavailable(engine_settings):
    client = EngineClient(engine_settings("http://127.0.0.1:1"))   # nothing listens there
    with pytest.raises(EngineUnavailable):
        client.render("x", None)


def test_render_timeout_is_engine_unavailable(engine_settings):
    state = EngineDoubleState(slow_render_sec=0.5)
    with run_engine_double_server(state) as base_url:
        client = EngineClient(engine_settings(base_url))
        with pytest.raises(EngineUnavailable):
            client.render("x", None, timeout=0.05)


def test_list_voices_maps_fields(engine_settings):
    state = EngineDoubleState()
    with run_engine_double_server(state) as base_url:
        client = EngineClient(engine_settings(base_url))
        voices = client.list_voices()
        assert [v.id for v in voices] == ["Hải Đăng", "Mai Anh"]
        assert voices[0].gender == "male" and voices[0].featured is True


@pytest.mark.asyncio
async def test_open_stream_yields_pcm_bytes(engine_settings):
    state = EngineDoubleState()
    with run_engine_double_server(state) as base_url:
        client = EngineClient(engine_settings(base_url))
        chunks = [c async for c in client.open_stream("Xin chào.", None)]
        assert b"".join(chunks)


@pytest.mark.asyncio
async def test_open_stream_truncation_raises_engine_unavailable(engine_settings):
    state = EngineDoubleState(truncate_stream=True)
    with run_engine_double_server(state) as base_url:
        client = EngineClient(engine_settings(base_url))
        with pytest.raises(EngineUnavailable):
            async for _ in client.open_stream("Xin chào.", None):
                pass

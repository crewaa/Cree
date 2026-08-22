"""
Tests for the Gemini client itself.

Every other AI test stubs `GeminiClient.generate`, which is right for testing
routers but means the client's own code — the part that changed when the SDK was
swapped — was covered by nothing. The migration from `google-generativeai` to
`google-genai` could not be exercised against the live API from a sandbox with no
route to Google, so these tests stand in for that: they assert the exact call
this code makes, against a fake shaped like the new SDK.

If Google changes the SDK surface again, these fail rather than production.
"""

import pytest

from app.core.config import settings
from app.modules.ai import ai_service
from app.modules.ai.ai_service import GeminiClient


class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _FakeAioModels:
    """Stands in for `client.aio.models`, recording how it was called."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    async def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.error:
            raise self.error
        return self.result


class _FakeClient:
    def __init__(self, models):
        self.aio = type("Aio", (), {"models": models})()


@pytest.fixture
def gemini(monkeypatch):
    """Build a GeminiClient whose SDK client is a fake, with a key configured."""
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    def build(result=None, error=None):
        models = _FakeAioModels(result=result, error=error)
        monkeypatch.setattr(
            ai_service.genai, "Client", lambda **kwargs: _FakeClient(models)
        )
        return GeminiClient(), models

    return build


# ---------------------------------------------------------------------------
# The call itself
# ---------------------------------------------------------------------------

async def test_generate_returns_the_model_text(gemini):
    client, models = gemini(result=_FakeResponse('{"ok": true}'))

    assert await client.generate("hello") == '{"ok": true}'
    assert models.calls[0]["contents"] == "hello"


async def test_the_call_asks_the_api_to_enforce_json(gemini):
    """
    Prompts ask for JSON, but asking is not enforcing. `response_mime_type` makes
    the API itself refuse to return anything else, which is what allows
    `extract_json` to be a fallback rather than the only defence.
    """
    client, models = gemini(result=_FakeResponse("{}"))
    await client.generate("hello")

    assert models.calls[0]["config"].response_mime_type == "application/json"


async def test_the_timeout_is_sent_in_milliseconds(gemini):
    """
    The setting is in seconds and the SDK wants milliseconds. Getting this wrong
    is silent: a 60 would become 60ms and every call would time out, or a 60000
    would become 16 hours and a hung request would pin a worker forever.
    """
    client, models = gemini(result=_FakeResponse("{}"))
    await client.generate("hello")

    expected = settings.gemini_timeout_seconds * 1000
    assert models.calls[0]["config"].http_options.timeout == expected


async def test_the_configured_model_is_used(gemini, monkeypatch):
    monkeypatch.setattr(settings, "gemini_model", "gemini-from-config")
    client, models = gemini(result=_FakeResponse("{}"))
    await client.generate("hello")

    assert models.calls[0]["model"] == "gemini-from-config"


def test_a_missing_api_key_fails_loudly(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiClient()


# ---------------------------------------------------------------------------
# Failure translation
# ---------------------------------------------------------------------------

async def test_a_429_becomes_the_rate_limit_error(gemini):
    """
    Routers turn RuntimeError into a 429 for the user. The old SDK forced this to
    be detected by searching the exception text; the new one carries a numeric
    code, so a reworded Google error can no longer become a 500.
    """
    class Throttled(Exception):
        code = 429

    client, _ = gemini(error=Throttled("RESOURCE_EXHAUSTED"))

    with pytest.raises(RuntimeError, match="quota"):
        await client.generate("hello")


async def test_quota_wording_is_still_caught_without_a_code(gemini):
    """Belt and braces: not every failure path carries a numeric code."""
    client, _ = gemini(error=Exception("429 RESOURCE_EXHAUSTED: quota exceeded"))

    with pytest.raises(RuntimeError, match="quota"):
        await client.generate("hello")


async def test_an_unrelated_error_is_not_disguised_as_a_quota_problem(gemini):
    """
    Translating everything into "quota exceeded" would send users away to wait
    for a window that was never the problem.
    """
    client, _ = gemini(error=ValueError("malformed request"))

    with pytest.raises(ValueError, match="malformed request"):
        await client.generate("hello")


async def test_an_empty_response_is_reported_clearly(gemini):
    """
    `.text` is None when the model returns no candidate — a safety block, for
    instance. Passing that on would surface as an AttributeError inside
    extract_json, far from the cause.
    """
    client, _ = gemini(result=_FakeResponse(None))

    with pytest.raises(ValueError, match="empty response"):
        await client.generate("hello")

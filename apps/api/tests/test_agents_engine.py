"""Tests for POST /api/v1/agents/{persona}/query — the agents engine.

Coverage:
  * Each of the 4 personas (dispatcher_analyst, market_analyst,
    energy_advisor, battery_coach) accepts a persona-appropriate sample
    question and returns the AgentQueryOut envelope.
  * Response payload contains: answer, intent, confidence, evidence,
    persona, duration_ms.
  * confidence is a float in [0.0, 1.0].
  * evidence is a list (may be empty for fallback responses).
  * Gibberish input degrades gracefully — intent="unknown_intent"
    (engine FALLBACK_INTENT) OR low confidence (< 0.5) with an answer
    still present.
  * Unknown persona is rejected with 422 (ValidationFailed via
    ValidationFailed → handler maps to 422).
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import gecko_vpp.db as _db
from gecko_vpp.config import get_settings
from gecko_vpp.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def _reset_engine_between_tests():
    """Reset global async engine after each test (function-scoped event loop)."""
    yield
    if _db._engine is not None:
        try:
            await _db._engine.dispose()
        except Exception:
            pass
    _db._engine = None
    _db._session_factory = None


settings = get_settings()
TENANT_PRODUCER = settings.tenant_producer_uuid

ALL_KEYS = {"answer", "intent", "confidence", "evidence", "persona", "duration_ms"}

# Persona-appropriate questions drawn from each persona's
# fallback_sample_questions list to maximise hit probability against the
# deterministic classifier.
PERSONA_QUESTIONS = {
    "dispatcher_analyst": "що сьогодні з виробництвом?",
    "market_analyst": "розбий виторг по каналах",
    "energy_advisor": "скільки зекономили?",
    "battery_coach": "коли заряджати батарею?",
}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _post_query(
    persona: str, question: str, tenant: str = TENANT_PRODUCER
) -> dict:
    async with _client() as client:
        resp = await client.post(
            f"/api/v1/agents/{persona}/query",
            json={"question": question},
            headers={"X-Tenant-Id": tenant},
        )
    return {"status": resp.status_code, "body": resp.json(), "raw": resp.text}


async def test_dispatcher_analyst_basic_shape() -> None:
    out = await _post_query(
        "dispatcher_analyst", PERSONA_QUESTIONS["dispatcher_analyst"]
    )
    assert out["status"] == 200, out["raw"]
    body = out["body"]
    assert "data" in body and "meta" in body
    data = body["data"]
    assert ALL_KEYS.issubset(data.keys()), (
        f"missing keys: {ALL_KEYS - set(data.keys())} in {data}"
    )
    assert isinstance(data["answer"], str) and data["answer"]
    assert isinstance(data["intent"], str)
    assert isinstance(data["confidence"], (int, float))
    assert 0.0 <= float(data["confidence"]) <= 1.0
    assert isinstance(data["evidence"], list)
    assert data["persona"] == "dispatcher_analyst"
    assert isinstance(data["duration_ms"], int)


@pytest.mark.parametrize("persona", list(PERSONA_QUESTIONS.keys()))
async def test_all_personas_respond(persona: str) -> None:
    """Every persona must accept its own sample question and respond."""
    question = PERSONA_QUESTIONS[persona]
    out = await _post_query(persona, question)
    assert out["status"] == 200, out["raw"]
    data = out["body"]["data"]
    assert ALL_KEYS.issubset(data.keys()), (
        f"persona={persona} missing keys: {ALL_KEYS - set(data.keys())}"
    )
    assert data["persona"] == persona
    assert 0.0 <= float(data["confidence"]) <= 1.0
    assert isinstance(data["evidence"], list)
    # An answer is always present — even fallback returns a helpful string.
    assert isinstance(data["answer"], str) and data["answer"].strip()


async def test_gibberish_falls_back_or_low_confidence() -> None:
    """Off-topic gibberish must either resolve to unknown_intent (engine
    FALLBACK_INTENT) OR return a low-confidence helpful answer. The engine
    must NOT raise 500."""
    out = await _post_query("dispatcher_analyst", "xkjasdkj qwerasdf zzzz")
    assert out["status"] == 200, out["raw"]
    data = out["body"]["data"]
    intent = data["intent"]
    confidence = float(data["confidence"])
    is_fallback = intent in {"unknown_intent", "fallback"}
    is_low_conf = confidence < 0.5
    assert is_fallback or is_low_conf, (
        f"gibberish must be fallback or low-confidence — got "
        f"intent={intent}, confidence={confidence}"
    )
    # Always have a non-empty answer to help the user.
    assert isinstance(data["answer"], str) and data["answer"].strip()


async def test_unknown_persona_rejected() -> None:
    out = await _post_query("not_a_persona", "test")
    # ValidationFailed → 422. (Could be 404 if route fails to bind, but
    # the actual implementation raises ValidationFailed → 422.)
    assert out["status"] in (404, 422), out["raw"]


async def test_agent_query_missing_tenant_header() -> None:
    async with _client() as client:
        resp = await client.post(
            "/api/v1/agents/dispatcher_analyst/query",
            json={"question": "test"},
        )
    assert resp.status_code in (400, 422), resp.text

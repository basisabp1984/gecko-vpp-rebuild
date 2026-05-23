"""Schemas for agents (stub surface)."""

from __future__ import annotations

from typing import Any

from gecko_vpp.schemas.common import GeckoModel


class AgentQueryIn(GeckoModel):
    question: str | None = None
    text: str | None = None
    context: dict[str, Any] = {}


class AgentQueryOut(GeckoModel):
    answer: str
    intent: str
    confidence: float
    evidence: list[Any] = []
    persona: str
    duration_ms: int


class VoiceSessionOut(GeckoModel):
    provider: str
    session_token: str | None = None
    websocket_url: str | None = None
    canned_scenarios: list[dict[str, Any]] = []
